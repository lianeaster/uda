import re
import shutil
import subprocess
import unittest

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from . import content
from .models import ContactRequest
from .views import constructor_catalog


class ConstructorPageTests(TestCase):
    """Конструктор курсів — публічна сторінка Академії, вхід із головної."""

    url = '/academy/constructor/'

    def test_page_is_public_and_loads_the_matrix(self):
        self.assertEqual(reverse('core:constructor'), self.url)
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        # Дані матриці, підбір і сама гра — три скрипти, саме в такому порядку.
        html = page.content.decode()
        scripts = [html.index(f'js/{name}.js') for name in
                   ('competency-data', 'course-engine', 'constructor')]
        self.assertEqual(scripts, sorted(scripts))
        self.assertContains(page, 'id="cc-catalog"')

    def test_home_starts_with_the_constructor(self):
        # Віджет стоїть у героя головної — перед усім іншим, що є на сторінці.
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertLess(html.index('id="cc-app"'), html.index('Кому це потрібно'))
        for part in ('js/constructor.js', 'id="cc-catalog"', 'id="zapys"',
                     f'action="{self.url}"'):
            self.assertIn(part, html)

    def test_home_and_courses_lead_to_the_constructor(self):
        for name in ('core:home', 'core:courses'):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), f'href="{self.url}"')

    def test_every_matrix_course_has_a_card(self):
        # Курс є в матриці, а картки на сайті немає — у результаті він лишився б
        # без опису й фото. id курсів матриці читаємо просто з її файла.
        source = (settings.BASE_DIR / 'static/js/competency-data.js').read_text(encoding='utf-8')
        block = source[source.index('const COURSES = ['):source.index('const COVERAGE')]
        matrix = set(re.findall(r"\{ id: '([\w-]+)'", block))
        self.assertEqual(len(matrix), 1 + len(content.COURSES) + len(content.MASTERCLASSES))
        self.assertEqual({card['id'] for card in constructor_catalog()}, matrix)


class CoursesPageTests(TestCase):
    """Сторінка курсів — ціни майстерень як на distillingacademy.com.ua/courses."""

    def test_every_workshop_shows_its_own_price(self):
        page = self.client.get(reverse('core:courses'))
        for title, price in (('Зернові дистиляти / горілка', 445),
                             ('Майстерня віскі та солодові дистиляти', 580),
                             ('Майстерня джину та настоянок', 445),
                             ('Майстерня сенсорного аналізу', 395),
                             ('Майстерня витримки', 395),
                             ('Правила спиртового бродіння', 395),
                             ('Майстерня фруктових дистилятів та бренді', 445),
                             ('Спецкурс-інтенсив Spirit Course', 670)):
            with self.subTest(course=title):
                self.assertRegex(page.content.decode(),
                                 rf'<h3>{re.escape(title)}</h3>\s*<p class="card-body">'
                                 rf'[^<]*</p>\s*<span class="card-kicker">Офлайн · {price} €</span>')
        self.assertNotContains(page, 'Онлайн · 980 €')


class ConstructorRequestTests(TestCase):
    url = '/academy/constructor/'
    data = {
        'name': 'Олена', 'phone': '+380501112233', 'consent': 'on',
        'interest': 'Конструктор: Майстерня джину та настоянок — 91%',
        'details': 'Рівень: Новачок\nНапій: Джин',
        'state': 'm=q&l=novice&d=gin&s=botan',
    }

    def test_request_keeps_what_the_constructor_picked(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, self.url + '?done=1')
        self.assertContains(self.client.get(response.url), 'Заявку отримано')
        request = ContactRequest.objects.get()
        self.assertEqual(request.source, ContactRequest.Source.CONSTRUCTOR)
        self.assertEqual(request.interest, self.data['interest'])
        self.assertEqual(request.details, self.data['details'])

    def test_request_without_a_pick_is_still_marked(self):
        self.client.post(self.url, {'name': 'Олена', 'phone': '+380501112233', 'consent': 'on'})
        request = ContactRequest.objects.get()
        self.assertEqual(request.source, ContactRequest.Source.CONSTRUCTOR)
        self.assertEqual(request.interest, 'Конструктор курсів')

    def test_invalid_request_returns_the_same_result(self):
        # Сторінка відновлює результат зі `state`, тож після помилки він мусить
        # повернутися разом із формою.
        response = self.client.post(self.url, {**self.data, 'phone': ''})
        self.assertContains(response, 'errorlist')
        self.assertContains(response, 'value="m=q&amp;l=novice&amp;d=gin&amp;s=botan"')
        self.assertFalse(ContactRequest.objects.exists())

    def test_details_are_capped(self):
        self.client.post(self.url, {**self.data, 'details': 'x' * 10_000})
        self.assertEqual(len(ContactRequest.objects.get().details), 4000)


@unittest.skipUnless(shutil.which('node'), 'правила підбору перевіряє node')
class ConstructorEngineTests(unittest.TestCase):
    """Правила підбору живуть у JS — ганяємо їхні тести на справжній матриці."""

    def test_engine_rules(self):
        run = subprocess.run(
            ['node', str(settings.BASE_DIR / 'tests/course-engine.test.js')],
            capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


class ConstructorPricesTests(TestCase):
    """Ціни в конструкторі — з платформи: години «Майстра» × ставки + комісія."""

    def setUp(self):
        import datetime as dt
        from decimal import Decimal

        from django.core.management import call_command
        from django.utils import timezone

        from schedule.models import EuroRate

        call_command('import_program', verbosity=0)
        EuroRate.objects.create(date=timezone.localdate(), rate=Decimal('50'))
        self.dt = dt

    def prices(self):
        import json
        page = self.client.get(reverse('core:constructor')).content.decode()
        raw = re.search(r'<script id="cc-prices" type="application/json">(.*?)</script>', page, re.S)
        return json.loads(raw.group(1))

    def test_every_paid_subject_of_the_matrix_has_a_price(self):
        prices = self.prices()
        source = (settings.BASE_DIR / 'static/js/competency-data.js').read_text(encoding='utf-8')
        block = source[source.index('const SUBJECTS = {'):source.index('const DOMAINS')]
        matrix = set(re.findall(r"'([\d.]+[ab]?)':\s*\[", block))
        # Випускна робота безкоштовна — решта предметів матриці мають ціну.
        self.assertEqual(set(prices['subjects']), matrix - {'10.9'})
        self.assertEqual(prices['subjects']['2.2'], {'hours': 4.0, 'uah': 10400})   # Бачурін
        self.assertEqual(prices['subjects']['8.1']['hours'], 3.0)                   # «8.2» у графіку
        self.assertEqual(prices['rate'], 50.0)
        self.assertEqual(prices['courses']['master']['uah'], 60000)
        self.assertEqual(prices['courses']['master']['earlyBird']['uah'], 55000)

    def test_only_what_the_student_pays_goes_public(self):
        raw = str(self.prices())
        for secret in ('teachers', 'academy', 'rate\': 2000', 'hourly'):
            self.assertNotIn(secret, raw)
