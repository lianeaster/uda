import datetime as dt
import re
import shutil
import subprocess
import unittest

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from . import content
from .models import ContactRequest
from . import views
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

    def test_master_shows_regular_and_early_bird_price(self):
        for name in ('core:courses', 'core:home'):
            with self.subTest(page=name):
                page = self.client.get(reverse(name))
                self.assertContains(page, '<div class="value">1200 €</div>'
                                          '<div class="value-note">Early Bird — 980 €</div>', html=True)
                self.assertContains(page, '<a class="btn btn-primary" href="/academy/courses/'
                                          'sertyfikatsiyna-prohrama-kurs-mayster-dystylyatsiyi/#zayavka">'
                                          'Записатися на курс</a>', html=True)

    def test_discount_is_announced_above_all_courses(self):
        self.assertContains(self.client.get(reverse('core:courses')),
                            'знижка 20% на всі курси')


class CoursePageTests(TestCase):
    """Своя сторінка в кожного курсу: опис, програма, лектори й запис."""

    def pages(self):
        for card in [content.FLAGSHIP, *content.COURSES]:
            yield card, content.COURSE_PAGES[card['id']]

    def test_every_course_has_a_page(self):
        self.assertEqual(set(content.COURSE_PAGES),
                         {content.FLAGSHIP['id'], *(c['id'] for c in content.COURSES)})
        for card, page in self.pages():
            with self.subTest(course=card['id']):
                url = reverse('core:course', args=[page['slug']])
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'{card["price_eur"]} €')
                for slug in page['lecturers']:
                    self.assertContains(response, content.LECTURERS_BY_SLUG[slug]['name'])
                for item in page['learn']:
                    self.assertContains(response, item)

    def test_courses_page_and_home_link_to_every_page(self):
        listing = self.client.get(reverse('core:courses'))
        home = self.client.get(reverse('core:home'))
        for card, page in self.pages():
            with self.subTest(course=card['id']):
                url = reverse('core:course', args=[page['slug']])
                self.assertContains(listing, f'href="{url}')
        for card in content.COURSES[:4]:
            url = reverse('core:course', args=[content.COURSE_PAGES[card['id']]['slug']])
            self.assertContains(home, f'href="{url}"')

    def test_master_programme_comes_from_its_schedule(self):
        from schedule import programs
        page = self.client.get(reverse('core:course', args=[content.COURSE_PAGES['master']['slug']]))
        for code, name, _format, items in programs.MODULES:
            self.assertContains(page, f'Модуль {code}. {name.rstrip(".")}')

    def test_a_start_date_that_has_passed_is_not_shown(self):
        for card, page in self.pages():
            start = page.get('start')
            if card['id'] == 'master' or start is None:
                continue
            with self.subTest(course=card['id']):
                response = self.client.get(reverse('core:course', args=[page['slug']]))
                if start >= dt.date.today():
                    self.assertContains(response, f'{start:%d.%m.%Y}')
                else:
                    self.assertNotContains(response, f'{start:%d.%m.%Y}')
                    self.assertContains(response, 'За набором групи')

    def test_unknown_course_is_404(self):
        self.assertEqual(self.client.get('/academy/courses/kurs-nemaye/').status_code, 404)

    def test_old_address_leads_to_the_page(self):
        response = self.client.get('/courses/kurs-maysternya-vytrymky/')
        self.assertRedirects(response, '/academy/courses/kurs-maysternya-vytrymky/',
                             status_code=301)

    def test_request_is_signed_with_the_course(self):
        url = reverse('core:course', args=['kurs-maysternya-vytrymky'])
        response = self.client.post(url, {
            'name': 'Олена', 'phone': '+380501112233', 'consent': 'on',
            'interest': 'щось інше',
        })
        self.assertRedirects(response, url + '?done=1#zayavka', fetch_redirect_response=False)
        enquiry = ContactRequest.objects.get()
        self.assertEqual(enquiry.interest, 'Запис на курс «Майстерня витримки»')
        self.assertEqual(enquiry.source, ContactRequest.Source.ACADEMY)
        self.assertContains(self.client.get(url + '?done=1'), 'Дякуємо!')

    def test_invalid_request_stays_on_the_page(self):
        url = reverse('core:course', args=['kurs-maysternya-vytrymky'])
        response = self.client.post(url, {'name': 'Олена'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactRequest.objects.exists())


class LecturerPageTests(TestCase):
    """Своя сторінка в кожного лектора: біографія, курси, теми в «Майстрі»."""

    def test_every_lecturer_has_a_page(self):
        for person in content.LECTURERS:
            with self.subTest(lecturer=person['slug']):
                page = self.client.get(reverse('core:lecturer', args=[person['slug']]))
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, f'<h1>{person["name"]}</h1>', html=True)
                for paragraph in content.LECTURER_PAGES[person['slug']]['about']:
                    self.assertContains(page, escape(paragraph))

    def test_every_lecturer_has_two_to_four_paragraphs_and_real_photos(self):
        self.assertEqual(set(content.LECTURER_PAGES), set(content.LECTURERS_BY_SLUG))
        for slug, page in content.LECTURER_PAGES.items():
            with self.subTest(lecturer=slug):
                self.assertTrue(2 <= len(page['about']) <= 4)
                self.assertTrue(page['sources'])
                self.assertLessEqual(len(page.get('gallery', [])), 5)
                for src, source in page.get('gallery', []):
                    self.assertTrue((settings.BASE_DIR / 'static/img/lecturers' / src).exists(), src)
                    self.assertTrue(source.startswith('http'))

    def test_photos_lie_in_a_stack_portrait_on_top(self):
        page = self.client.get(reverse('core:lecturer', args=['ivan-bachurin']))
        gallery = content.LECTURER_PAGES['ivan-bachurin']['gallery']
        self.assertContains(page, 'data-stack')
        self.assertContains(page, 'class="stack-card"', count=1 + len(gallery))
        self.assertContains(page, 'data-pos="0"><img src="/static/img/lecturers/ivan-bachurin.jpg"')
        self.assertContains(page, 'data-go=', count=1 + len(gallery))
        for src, _source in gallery:
            self.assertContains(page, f'src="/static/img/lecturers/{src}"')
        # Лише портрет — одна картка, без крапок.
        page = self.client.get(reverse('core:lecturer', args=['andre-pryda']))
        self.assertContains(page, 'class="stack-card"', count=1)
        self.assertNotContains(page, 'data-go=')

    def test_lecturers_page_shows_photo_cards(self):
        page = self.client.get(reverse('core:lecturers'))
        self.assertContains(page, 'class="print-card"', count=len(content.LECTURERS))
        self.assertContains(page, 'src="/static/img/lecturers/ivan-bachurin.jpg"')
        # З-під портрета визирає ще одне фото — лише в тих, у кого воно є.
        with_more = [p for p in content.LECTURER_PAGES.values() if p.get('gallery')]
        self.assertContains(page, 'class="print-card-under"', count=len(with_more))

    def test_every_portrait_is_a_4_by_5_photo_card(self):
        # Кругів більше немає: портрет — прямокутна фотокартка без кутів-тла.
        from PIL import Image
        for person in content.LECTURERS:
            with self.subTest(lecturer=person['slug']):
                with Image.open(settings.BASE_DIR / 'static/img' / person['photo']) as image:
                    self.assertEqual(image.size, (640, 800))

    def test_page_lists_the_courses_the_lecturer_teaches(self):
        page = self.client.get(reverse('core:lecturer', args=['andre-pryda']))
        aging = reverse('core:course', args=[content.COURSE_PAGES['aging']['slug']])
        self.assertContains(page, f'href="{aging}"')
        self.assertContains(page, 'Курс, який веде')
        for other in ('grain', 'master'):
            url = reverse('core:course', args=[content.COURSE_PAGES[other]['slug']])
            self.assertNotContains(page, f'href="{url}"')

    def test_master_topics_come_from_its_schedule(self):
        page = self.client.get(reverse('core:lecturer', args=['maryna-chekhun']))
        self.assertContains(page, 'Теми в курсі «Майстер дистиляції»')
        for topic in ('Вода', 'Купажування', 'Основи дегустації продукції. Вимоги до дегустаторів'):
            self.assertContains(page, f'<li>{topic}</li>', html=True)
        # Платформний логін «manager» — це картка Катерини Камишевої.
        page = self.client.get(reverse('core:lecturer', args=['kateryna-kamysheva']))
        self.assertContains(page, '<li>Маркетингова складова</li>', html=True)

    def test_lecturer_without_courses_has_no_course_section(self):
        page = self.client.get(reverse('core:lecturer', args=['olga-burkanova']))
        self.assertNotContains(page, 'які веде')
        self.assertNotContains(page, 'Теми в курсі')

    def test_lecturer_cards_link_to_their_pages(self):
        url = reverse('core:lecturer', args=['ivan-bachurin'])
        course = reverse('core:course', args=[content.COURSE_PAGES['spirit']['slug']])
        for page in (reverse('core:lecturers'), reverse('core:home'), course):
            with self.subTest(page=page):
                self.assertContains(self.client.get(page), f'href="{url}"')

    def test_unknown_lecturer_is_404(self):
        self.assertEqual(self.client.get('/academy/lecturers/nikhto/').status_code, 404)


class GraduatesShelfTests(TestCase):
    """Пляшки випускників: стрічка на головній, кілька фото — на сторінці курсу."""

    photos = sum(len(g['photos']) for g in content.GRADUATES)

    def test_home_shelf_follows_the_testimonials(self):
        # Не під героєм і не впритул до стрічки лекторів: між ними — відгуки.
        html = self.client.get(reverse('core:home')).content.decode()
        shelf = html.index('id="polytsia"')
        self.assertLess(html.index('class="lecturer-reel"'), html.index('data-reveal>Відгуки</span>'))
        self.assertLess(html.index('data-reveal>Відгуки</span>'), shelf)
        # Кожне фото двічі: другий набір — для безшовного повтору.
        self.assertEqual(html.count('class="grad-photo"'), 2 * self.photos)

    def test_course_page_shows_only_its_own_graduates(self):
        for course_id, page in content.COURSE_PAGES.items():
            with self.subTest(course=course_id):
                html = self.client.get(reverse('core:course', args=[page['slug']])).content.decode()
                self.assertNotIn('id="polytsia"', html)
                ours = {g['id'] for g in content.GRADUATES if course_id in g['courses']}
                shown = set(re.findall(r'class="grad-photo"[^>]*><img src="/static/img/graduates/([\w-]+)/', html))
                self.assertLessEqual(shown, ours)
                if ours:
                    self.assertContains(self.client.get(reverse('core:course', args=[page['slug']])),
                                        'Що роблять випускники курсу')
                    self.assertTrue(1 <= html.count('class="grad-photo"') <= 5)
                else:
                    self.assertNotIn('Що роблять випускники курсу', html)

    def test_brands_take_turns(self):
        photos = views.graduate_photos()
        first_round = [p['brand'] for p in photos[:len(content.GRADUATES)]]
        self.assertEqual(len(set(first_round)), len(content.GRADUATES))
        master = [p['brand'] for p in views.graduate_photos('master')[:4]]
        self.assertEqual(len(set(master)), 4)

    def test_every_photo_exists_and_links_to_the_brand(self):
        for graduate in content.GRADUATES:
            with self.subTest(graduate=graduate['id']):
                self.assertTrue(graduate['link'][1].startswith('https://'))
                for course_id in graduate['courses']:
                    self.assertIn(course_id, content.COURSE_PAGES)
                for src, source in graduate['photos']:
                    self.assertTrue((settings.BASE_DIR / 'static/img/graduates' / src).exists(), src)
                    self.assertTrue(source.startswith('http'))
        html = self.client.get(reverse('core:home')).content.decode()
        for link in re.findall(r'<a class="grad-photo"[^>]*>', html):
            self.assertIn('rel="noopener"', link)


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
