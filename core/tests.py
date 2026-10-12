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
