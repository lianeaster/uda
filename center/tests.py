import re

from django.test import TestCase
from django.urls import reverse

from core.models import ContactRequest
from . import content


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


class MapTests(TestCase):
    """Карта: Центр → послуги (головне) → дві академії."""

    def test_map_leads_with_services(self):
        html = self.client.get('/').content.decode()
        for unit in content.SERVICES + [content.INCUBATOR]:
            with self.subTest(unit=unit['slug']):
                self.assertIn(f'href="/services/#{unit["slug"]}"', html)
        self.assertLess(html.index('Послуги Центру'), html.index('id="akademii"'))

    def test_map_links_both_academies(self):
        html = self.client.get('/').content.decode()
        for academy in content.ACADEMIES:
            with self.subTest(academy=academy['slug']):
                self.assertIn(f'class="u-map-node" href="{reverse(academy["url_name"])}"', html)
                self.assertIn(academy['name'], html)

    def test_home_is_about_services_not_study(self):
        # Перший екран — про дослідження й продукт; вхід на платформу — нижче.
        html = self.client.get('/').content.decode()
        hero = html[html.index('class="u-hero"'):html.index('id="pro-centr"')]
        self.assertIn('Досліджуємо сировину', hero)
        self.assertNotIn('академі', hero.lower())
        self.assertNotIn('навчальна платформа', hero.lower())
        self.assertIn(f'href="{reverse("accounts:login")}"', html)

    def test_platform_header_names_the_center(self):
        # Платформа одна на обидві академії — під її назвою Центр, а не Академія.
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, f'<span class="brand-sub">{content.NAME}</span>', html=True)


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
    def test_every_section_has_an_anchor(self):
        response = self.client.get(reverse('center:services'))
        slugs = [unit['slug'] for unit in content.SERVICES + [content.INCUBATOR]]
        for slug in slugs + ['academies']:
            with self.subTest(slug=slug):
                self.assertContains(response, f'id="{slug}"')

    def test_services_start_with_research_and_consulting(self):
        self.assertEqual([unit['slug'] for unit in content.SERVICES[:3]], ['lab', 'product', 'pilot'])

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
        html = self.client.get('/').content.decode()
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
        html = self.client.get('/').content.decode()
        self.assertIn('data-plan-filter', html)
        self.assertIn('data-uses="distilling fermentation"', html)
        for direction in content.DIRECTIONS:
            self.assertIn(f'data-direction="{direction["slug"]}"', html)


class CenterContactTests(TestCase):
    data = {'name': 'Олена', 'phone': '+380501112233', 'interest': '20 т гарбуза',
            'consent': 'on'}

    def test_center_request_is_marked_as_center(self):
        response = self.client.post('/', self.data)
        self.assertContains(response, 'Дякуємо!')
        request = ContactRequest.objects.get()
        self.assertEqual(request.source, ContactRequest.Source.CENTER)
        self.assertEqual(request.interest, '20 т гарбуза')

    def test_academy_request_stays_academy(self):
        self.client.post(reverse('core:lecturers'), self.data)
        self.assertEqual(ContactRequest.objects.get().source, ContactRequest.Source.ACADEMY)

    def test_invalid_request_shows_errors_and_saves_nothing(self):
        response = self.client.post('/', {'name': 'Олена'})
        self.assertContains(response, 'u-error')
        self.assertFalse(ContactRequest.objects.exists())
