import re

from django.test import TestCase
from django.urls import reverse

from core.models import ContactRequest
from . import content


class HierarchyTests(TestCase):
    """Центр — головна «парасолька», Академія — його підрозділ під /academy/."""

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


class MapTests(TestCase):
    """Карта: Центр → академії за напрямами → одна платформа і спільна база."""

    def test_distilling_is_the_only_live_academy_and_one_of_many(self):
        live = [a for a in content.ACADEMIES if a.get('live')]
        self.assertEqual([a['slug'] for a in live], ['distilling'])
        self.assertGreater(len(content.ACADEMIES), 1)

    def test_map_links_every_academy(self):
        html = self.client.get('/').content.decode()
        for academy in content.ACADEMIES:
            with self.subTest(academy=academy['slug']):
                href = '/academy/' if academy.get('live') else f'/directions/#{academy["slug"]}'
                self.assertIn(f'href="{href}"', html)
                self.assertIn(academy['title'], html)

    def test_map_links_the_shared_base_and_platform(self):
        html = self.client.get('/').content.decode()
        for unit in content.BASE:
            with self.subTest(unit=unit['slug']):
                self.assertIn(f'href="/directions/#{unit["slug"]}"', html)
        self.assertIn(f'href="{reverse("accounts:login")}"', html)

    def test_directions_map_links_stay_on_the_page(self):
        response = self.client.get(reverse('center:directions'))
        self.assertContains(response, 'href="#soft-drinks"')

    def test_platform_header_names_the_center(self):
        # Платформа одна на всі академії — під її назвою Центр, а не Академія.
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, f'<span class="brand-sub">{content.NAME}</span>', html=True)


class DirectionsTests(TestCase):
    def test_every_section_has_an_anchor(self):
        response = self.client.get(reverse('center:directions'))
        slugs = [a['slug'] for a in content.ACADEMIES + content.BASE + [content.INCUBATOR]]
        for slug in slugs + ['academies', 'platform', 'base']:
            with self.subTest(slug=slug):
                self.assertContains(response, f'id="{slug}"')


class FloorPlanTests(TestCase):
    def test_svg_coordinates_are_not_localized(self):
        # Українська локаль пише дроби з комою — у SVG це зламало б план.
        html = self.client.get('/').content.decode()
        svg = html[html.index('<svg viewBox'):html.index('</svg>', html.index('<svg viewBox'))]
        self.assertFalse(re.search(r'(?:x|y|width|height)="\d+,\d', svg))
        self.assertIn('x="101.0"', svg)


class SharedSpaceTests(TestCase):
    """Приміщення спільні: кожне служить академіям, а не одному напряму."""

    def test_rooms_name_only_real_academies(self):
        slugs = {a['slug'] for a in content.ACADEMIES}
        for room in content.PLAN_ROOMS:
            with self.subTest(room=room['name']):
                self.assertTrue(set(room['uses']) <= slugs)

    def test_every_academy_has_a_place_to_work(self):
        # Нова академія без жодного цеху чи зали — це дірка в плані.
        for academy in content.ACADEMIES:
            with self.subTest(academy=academy['slug']):
                self.assertTrue(any(academy['slug'] in room['uses'] for room in content.PLAN_ROOMS))

    def test_plan_marks_rooms_for_the_academy_filter(self):
        html = self.client.get('/').content.decode()
        self.assertIn('data-plan-filter', html)
        self.assertIn('data-uses="distilling wine fermentation"', html)
        for academy in content.ACADEMIES:
            self.assertIn(f'data-academy="{academy["slug"]}"', html)


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
