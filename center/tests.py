import re

from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from core.models import ContactRequest
from . import content, pages
from .models import News


class HierarchyTests(TestCase):
    """Центр — головна «парасолька», академії — його підрозділи.

    Академія дистиляції живе під /academy/ (так склалося: вона була першою),
    харчова — під /food-academy/.
    """

    def test_root_is_the_center(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'center/home.html')
        self.assertContains(response, 'Український центр')

    def test_academy_lives_under_academy(self):
        self.assertEqual(reverse('core:home'), '/academy/')
        self.assertEqual(reverse('core:courses'), '/academy/courses/')
        self.assertEqual(reverse('core:lecturers'), '/academy/lecturers/')
        self.assertTemplateUsed(self.client.get('/academy/'), 'core/home.html')

    def test_old_academy_links_redirect_permanently(self):
        for old, new in (('/courses/', '/academy/courses/'),
                         ('/lecturers/', '/academy/lecturers/')):
            with self.subTest(old=old):
                self.assertRedirects(self.client.get(old), new,
                                     status_code=301, fetch_redirect_response=False)

    def test_center_links_to_academy(self):
        response = self.client.get('/')
        self.assertContains(response, 'href="/academy/"')

    def test_academy_pages_point_up_to_the_center(self):
        for url in ('/academy/', '/academy/courses/', '/academy/lecturers/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="umbrella"')
                self.assertContains(response, content.NAME)

    def test_platform_has_no_umbrella_strip(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertNotContains(response, 'class="umbrella"')


class TwoAcademiesTests(TestCase):
    """Академій рівно дві: дистиляції та харчова. Напрями — не академії."""

    def test_only_two_academies(self):
        self.assertEqual([a['slug'] for a in content.ACADEMIES], ['distilling', 'food'])
        self.assertEqual(reverse(content.ACADEMIES[0]['url_name']), '/academy/')
        self.assertEqual(reverse(content.ACADEMIES[1]['url_name']), '/food-academy/')

    def test_food_academy_takes_every_direction_but_alcohol(self):
        food = {d['slug'] for d in content.FOOD_DIRECTIONS}
        self.assertEqual({d['slug'] for d in content.DIRECTIONS} - food, {'distilling'})
        self.assertNotIn('wine', food)
        self.assertEqual(len(food), 7)

    def test_no_per_direction_academies_left_on_the_site(self):
        for url in ('/', reverse('center:services'), reverse('center:food_academy')):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                for gone in ('Академія снеків', 'Академія меду', 'Академія вина',
                             'Академія ферментації', 'багато академій'):
                    self.assertNotIn(gone, html)


class StructureTests(TestCase):
    """Розділи за структурою керівництва. Чотири послуги — не окремі
    сторінки, а блоки однієї «Що ми робимо»."""

    sections = ['center:home', 'center:about', 'center:services', 'center:learning',
                'center:news', 'center:contacts']

    def test_every_section_opens(self):
        for url_name in self.sections:
            with self.subTest(url_name=url_name):
                self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

    def test_menu_leads_to_every_section(self):
        html = self.client.get('/').content.decode()
        header = html[html.index('<header'):html.index('</header>')]
        for url_name in self.sections[1:]:
            with self.subTest(url_name=url_name):
                self.assertIn(f'href="{reverse(url_name)}"', header)

    def test_services_are_blocks_of_one_page(self):
        html = self.client.get(reverse('center:services')).content.decode()
        jump = html[html.index('class="u-jump"'):]
        jump = jump[:jump.index('</nav>')]
        for name, anchor in pages.SERVICE_ORDER.items():
            with self.subTest(service=name):
                self.assertIn(f'id="{anchor}"', html)
                self.assertIn(f'href="#{anchor}"', jump)
                self.assertIn(pages.SERVICES[name]['title'], html)
        self.assertIn('Проєкти та пілотне виробництво', html)
        for old in ('/product-development/', '/consulting/', '/projects/', '/laboratory/'):
            with self.subTest(old=old):
                self.assertEqual(self.client.get(old).status_code, 404)

    def test_current_section_is_marked_in_the_menu(self):
        html = self.client.get(reverse('center:services')).content.decode()
        header = html[html.index('<header'):html.index('</header>')]
        self.assertIn(f'<a href="{reverse("center:services")}" aria-current="page">', header)

    def test_home_hero_follows_the_brief(self):
        html = self.client.get('/').content.decode()
        hero = html[html.index('class="u-hero"'):html.index('id="pro-centr"')]
        self.assertIn('що створюють', hero)
        self.assertIn('Досліджуємо.', hero)
        self.assertIn('Обговорити мій проєкт', hero)
        self.assertIn('Наші можливості', hero)
        self.assertNotIn('академі', hero.lower())
        self.assertNotIn('навчальна платформа', hero.lower())

    def test_home_capabilities_lead_to_their_blocks(self):
        html = self.client.get('/').content.decode()
        services = reverse('center:services')
        for anchor in pages.SERVICE_ORDER.values():
            with self.subTest(anchor=anchor):
                self.assertIn(f'class="u-card" href="{services}#{anchor}"', html)
        self.assertIn(f'class="u-card" href="{reverse("center:learning")}"', html)

    def test_footer_leads_to_each_service(self):
        html = self.client.get('/').content.decode()
        footer = html[html.index('<footer'):html.index('</footer>')]
        for anchor in pages.SERVICE_ORDER.values():
            with self.subTest(anchor=anchor):
                self.assertIn(f'href="{reverse("center:services")}#{anchor}"', footer)

    def test_every_page_ends_with_the_shared_call(self):
        for url_name in self.sections[1:-1]:
            with self.subTest(url_name=url_name):
                self.assertContains(self.client.get(reverse(url_name)), 'class="u-closing"')
        # На головній свій заклик, на «Контактах» — сама форма.
        self.assertNotContains(self.client.get('/'), 'class="u-closing"')
        self.assertNotContains(self.client.get(reverse('center:contacts')), 'class="u-closing"')

    def test_buttons_bring_their_topic_to_contacts(self):
        services = self.client.get(reverse('center:services'))
        blocks = [(name, page, self.client.get(reverse(f'center:{name}')))
                  for name, page in pages.PAGES.items()]
        blocks += [(name, part, services) for name, part in pages.SERVICES.items()]
        for name, page, response in blocks:
            topic = page['cta']['topic']
            href = reverse('center:contacts') + (f'?tema={topic}' if topic else '')
            with self.subTest(block=name):
                self.assertContains(response, f'href="{href}">{page["cta"]["label"]}<')
            if topic:
                self.assertIn(topic, dict(pages.TOPICS))

    def test_learning_page_lists_both_academies(self):
        html = self.client.get(reverse('center:learning')).content.decode()
        for academy in content.ACADEMIES:
            with self.subTest(academy=academy['slug']):
                self.assertIn(academy['name'], html)
                self.assertIn(f'href="{reverse(academy["url_name"])}"', html)

    def test_lab_does_not_claim_accreditation(self):
        self.assertContains(self.client.get(reverse('center:services')), 'не є акредитованими')


class PlatformBrandTests(TestCase):
    """Навчальна платформа UFIC вбрана у фарби Центру, а не Академії дистиляції.

    Розмітка в неї спільна з сайтом Академії (`base.html`), тож тему вмикає
    клас на <html> і окремий файл стилів — саме їх і перевіряємо.
    """

    def setUp(self):
        self.page = self.client.get(reverse('accounts:login'))
        self.html = self.page.content.decode()

    def test_platform_wears_the_center_theme(self):
        self.assertIn('<html lang="uk" class="platform">', self.html)
        self.assertIn('css/platform.css', self.html)
        self.assertLess(self.html.index('css/style.css'), self.html.index('css/platform.css'))

    def test_academy_site_keeps_its_own_look(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('<html lang="uk">', html)
        self.assertNotIn('css/platform.css', html)

    def test_platform_is_named_after_ufic_everywhere(self):
        self.assertEqual(content.PLATFORM_NAME, 'Навчальна платформа UFIC')
        self.assertContains(self.page, f'<title>Вхід — {content.PLATFORM_NAME}</title>', html=True)
        self.assertIn(f'<meta property="og:site_name" content="{content.PLATFORM_NAME}">', self.html)
        self.assertIn(f'alt="{content.PLATFORM_NAME}"', self.html)
        self.assertNotIn('Українська Академія Дистиляції', self.html)

    def test_platform_does_not_preload_the_academy_assets(self):
        # Фото героя (майже 2 МБ) і шрифти Академії платформі не потрібні.
        self.assertNotIn('rel="preload" as="image"', self.html)
        self.assertNotIn('rel="preload" as="font"', self.html)

    def test_login_leads_to_the_center_and_both_academies(self):
        # Платформа одна на всіх: зі входу видно і Центр, і кожну академію —
        # у шапці й під карткою входу, а не лише в підвалі.
        header = self.html[self.html.index('<header'):self.html.index('</header>')]
        main = self.html[self.html.index('<main'):self.html.index('</main>')]
        for part in (header, main):
            for url_name in ('center:home', 'core:home', 'center:food_academy'):
                with self.subTest(url_name=url_name):
                    self.assertIn(f'href="{reverse(url_name)}"', part)
        self.assertIn(content.FOOD_ACADEMY_NAME, main)

    def test_platform_footer_belongs_to_the_center(self):
        footer = self.html[self.html.index('<footer'):self.html.index('</footer>')]
        for url_name in ('center:home', 'center:services', 'core:home', 'center:food_academy'):
            with self.subTest(url_name=url_name):
                self.assertIn(f'href="{reverse(url_name)}"', footer)
        self.assertIn('Ukrainian Food Innovation Center', footer)
        self.assertNotIn('18+', footer)


class MobileMenuTests(TestCase):
    """На вузькому екрані меню кожного сайту ховається під сендвіч.

    Кнопка називає своє меню в `aria-controls` — на цьому тримається і скрипт
    (static/js/menu.js), і читачка екрана, тож перевіряємо саме цю пару.
    """

    def test_every_public_header_has_a_sandwich_wired_to_its_menu(self):
        pages = [
            (reverse('center:home'), 'u-nav'),
            (reverse('center:services'), 'u-nav'),
            (reverse('center:food_academy'), 'u-nav'),
            (reverse('core:home'), 'main-nav'),
            (reverse('core:courses'), 'main-nav'),
            (reverse('accounts:login'), 'main-nav'),
        ]
        for url, nav_id in pages:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                header = html[html.index('<header'):html.index('</header>')]
                self.assertIn('data-nav-toggle', header)
                self.assertIn(f'aria-controls="{nav_id}"', header)
                self.assertIn(f'id="{nav_id}"', header)
                # Без скрипта кнопки немає, а меню лишається розгорнутим.
                self.assertIn("classList.add('js')", html)
                self.assertIn('js/menu.js', html)


class ServicesTests(TestCase):
    def test_old_directions_address_redirects(self):
        self.assertRedirects(self.client.get('/directions/'), '/services/',
                             status_code=301, fetch_redirect_response=False)


class FoodAcademyTests(TestCase):
    url = '/food-academy/'
    data = {'name': 'Олена', 'phone': '+380501112233', 'interest': 'Снеки', 'consent': 'on'}

    def test_page_is_in_the_center_brand_and_points_up(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'center/base.html')
        self.assertContains(response, 'css/center.css')
        self.assertContains(response, 'class="u-umbrella"')
        self.assertContains(response, content.FOOD_ACADEMY_NAME)
        self.assertContains(response, 'href="/academy/"')

    def test_every_food_direction_has_a_card(self):
        html = self.client.get(self.url).content.decode()
        for direction in content.FOOD_DIRECTIONS:
            with self.subTest(direction=direction['slug']):
                self.assertIn(f'id="{direction["slug"]}"', html)
                self.assertIn(direction['title'], html)
        self.assertNotIn('id="distilling"', html)

    def test_direction_link_prefills_the_request(self):
        response = self.client.get(self.url, {'napryam': 'snacks'})
        self.assertEqual(response.context['form'].initial, {'interest': 'Снеки'})
        self.assertEqual(self.client.get(self.url, {'napryam': 'wine'}).context['form'].initial, {})

    def test_request_is_marked_as_food_academy(self):
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'Дякуємо!')
        self.assertEqual(ContactRequest.objects.get().source, ContactRequest.Source.FOOD_ACADEMY)

    def test_invalid_request_shows_errors_and_saves_nothing(self):
        response = self.client.post(self.url, {'name': 'Олена'})
        self.assertContains(response, 'u-error')
        self.assertFalse(ContactRequest.objects.exists())

    def test_distilling_academy_links_to_its_sibling(self):
        self.assertContains(self.client.get('/academy/'), f'href="{self.url}"')


class FloorPlanTests(TestCase):
    def test_svg_coordinates_are_not_localized(self):
        # Українська локаль пише дроби з комою — у SVG це зламало б план.
        html = self.client.get(reverse('center:about')).content.decode()
        svg = html[html.index('<svg viewBox'):html.index('</svg>', html.index('<svg viewBox'))]
        self.assertFalse(re.search(r'(?:x|y|width|height)="\d+,\d', svg))
        self.assertIn('x="101.0"', svg)


class SharedSpaceTests(TestCase):
    """Приміщення спільні: кожне служить напрямам, а не одному продукту."""

    def test_rooms_name_only_real_directions(self):
        slugs = {d['slug'] for d in content.DIRECTIONS}
        for room in content.PLAN_ROOMS:
            with self.subTest(room=room['name']):
                self.assertTrue(set(room['uses']) <= slugs)

    def test_every_direction_has_a_place_to_work(self):
        # Новий напрям без жодного цеху чи зали — це дірка в плані.
        for direction in content.DIRECTIONS:
            with self.subTest(direction=direction['slug']):
                self.assertTrue(any(direction['slug'] in room['uses'] for room in content.PLAN_ROOMS))

    def test_plan_marks_rooms_for_the_direction_filter(self):
        html = self.client.get(reverse('center:about')).content.decode()
        self.assertIn('data-plan-filter', html)
        self.assertIn('data-uses="distilling fermentation"', html)
        for direction in content.DIRECTIONS:
            self.assertIn(f'data-direction="{direction["slug"]}"', html)


class CenterContactTests(TestCase):
    url = '/contacts/'
    data = {'name': 'Олена', 'company': 'ФГ «Гарбуз»', 'phone': '+380501112233',
            'interest': 'Розробка харчового продукту', 'details': '20 т гарбуза',
            'consent': 'on'}

    def test_center_request_is_marked_as_center(self):
        response = self.client.post(self.url, self.data)
        self.assertContains(response, 'Дякуємо!')
        request = ContactRequest.objects.get()
        self.assertEqual(request.source, ContactRequest.Source.CENTER)
        self.assertEqual(request.company, 'ФГ «Гарбуз»')
        self.assertEqual(request.interest, 'Розробка харчового продукту')
        self.assertEqual(request.details, '20 т гарбуза')

    def test_form_offers_every_topic(self):
        html = self.client.get(self.url).content.decode()
        for _, label in pages.TOPICS:
            with self.subTest(topic=label):
                self.assertIn(f'<option value="{label}">{label}</option>', html)

    def test_topic_from_the_address_is_preselected(self):
        response = self.client.get(self.url, {'tema': 'lab'})
        self.assertEqual(response.context['form'].initial, {'interest': 'Лабораторні дослідження'})
        self.assertEqual(self.client.get(self.url, {'tema': 'wine'}).context['form'].initial, {})

    def test_unknown_topic_is_rejected(self):
        response = self.client.post(self.url, {**self.data, 'interest': 'Вино'})
        self.assertContains(response, 'u-error')
        self.assertFalse(ContactRequest.objects.exists())

    def test_academy_request_stays_academy(self):
        self.client.post(reverse('core:lecturers'), self.data)
        self.assertEqual(ContactRequest.objects.get().source, ContactRequest.Source.ACADEMY)

    def test_invalid_request_shows_errors_and_saves_nothing(self):
        response = self.client.post(self.url, {'name': 'Олена'})
        self.assertContains(response, 'u-error')
        self.assertFalse(ContactRequest.objects.exists())


class NewsTests(TestCase):
    """Новини пишуть в адмінці; на сайті — лише опубліковані."""

    def setUp(self):
        self.post = News.objects.create(
            title='Центр відкрив набір', slug='nabir', summary='Коротко про набір.',
            body='Перший абзац.\n\nДругий абзац.', is_published=True)
        News.objects.create(title='Чернетка', slug='chernetka', summary='—', body='—')

    def test_list_shows_only_published(self):
        response = self.client.get(reverse('center:news'))
        self.assertContains(response, 'Центр відкрив набір')
        self.assertNotContains(response, 'Чернетка')
        self.assertContains(response, f'href="{self.post.get_absolute_url()}"')

    def test_post_page_and_hidden_draft(self):
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, '<p>Другий абзац.</p>', html=True)
        self.assertEqual(self.client.get('/news/chernetka/').status_code, 404)

    def test_home_shows_latest_news_only_when_there_are_any(self):
        self.assertContains(self.client.get('/'), 'Переглянути всі новини')
        News.objects.all().delete()
        self.assertNotContains(self.client.get('/'), 'Переглянути всі новини')

    def test_empty_section_says_so(self):
        News.objects.all().delete()
        self.assertContains(self.client.get(reverse('center:news')), escape(pages.NEWS['empty']))

    def test_every_rubric_is_described(self):
        self.assertEqual(set(pages.NEWS['rubrics']), set(News.Rubric.values))
