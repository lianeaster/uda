import datetime as dt
import os
import tempfile
from html.parser import HTMLParser

from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from core import content

from .models import User

# Найменший валідний PNG — для перевірки завантаження фото.
ONE_PIXEL_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
    b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


class ImportLecturersTests(TestCase):
    """Імпорт лекторів публічного сайту в список викладачів платформи."""

    def import_lecturers(self, **options):
        call_command('import_lecturers', verbosity=0, **options)

    def test_every_lecturer_becomes_a_teacher_account(self):
        self.import_lecturers()
        teachers = User.objects.with_role(User.Role.TEACHER)
        self.assertEqual(teachers.count(), len(content.LECTURERS))
        self.assertEqual(
            {t.get_full_name() for t in teachers},
            {lecturer['name'] for lecturer in content.LECTURERS},
        )

    def test_logins_come_from_the_photo_slug(self):
        self.import_lecturers()
        self.assertTrue(User.objects.filter(username='olexandr-ryabtsev').exists())
        self.assertTrue(User.objects.filter(username='kateryna-kamysheva').exists())

    def test_a_person_already_on_the_platform_is_found_by_name_not_duplicated(self):
        """Катерина Камишева працює під логіном `manager` — імпорт мусить
        знайти її за ПІБ, а не завести другий акаунт під слагом."""
        kamysheva = User.objects.create_user(
            username='manager', password='pw', first_name='Катерина',
            last_name='Камишева', roles=[User.Role.MANAGER, User.Role.TEACHER])
        self.import_lecturers()
        self.assertFalse(User.objects.filter(username='kateryna-kamysheva').exists())
        self.assertEqual(User.objects.filter(last_name='Камишева').count(), 1)
        kamysheva.refresh_from_db()
        self.assertEqual(kamysheva.username, 'manager')

    def test_two_people_with_the_same_name_are_left_for_a_human_to_sort_out(self):
        for username in ('k1', 'k2'):
            User.objects.create_user(
                username=username, password='pw', first_name='Катерина',
                last_name='Камишева', roles=[User.Role.TEACHER])
        self.import_lecturers()
        # Навмання не вибираємо й двійника не створюємо — обидва лишаються.
        self.assertFalse(User.objects.filter(username='kateryna-kamysheva').exists())
        self.assertEqual(User.objects.filter(last_name='Камишева').count(), 2)

    def test_imported_accounts_cannot_be_logged_into_until_a_password_is_set(self):
        self.import_lecturers()
        for teacher in User.objects.with_role(User.Role.TEACHER):
            with self.subTest(username=teacher.username):
                self.assertFalse(teacher.has_usable_password())

    def test_running_twice_creates_nothing_new(self):
        self.import_lecturers()
        before = set(User.objects.values_list('pk', flat=True))
        self.import_lecturers()
        self.assertEqual(set(User.objects.values_list('pk', flat=True)), before)

    def test_dry_run_writes_nothing(self):
        self.import_lecturers(dry_run=True)
        self.assertEqual(User.objects.count(), 0)

    def test_a_lecturer_who_manages_rather_than_teaches_keeps_her_roles(self):
        """Ольга Бурканова — арт-директорка Академії: у списку лекторів вона є,
        а на платформі керує. Роль «Викладач» їй не додаємо, але й лектором
        бути не забороняємо."""
        art_director = User.objects.create_user(
            username='olga-burkanova', password='pw', first_name='Ольга',
            last_name='Бурканова', roles=[User.Role.MANAGER])
        self.import_lecturers()
        art_director.refresh_from_db()
        del art_director._roles_cache
        self.assertEqual(art_director.roles, {User.Role.MANAGER})
        self.assertEqual(User.objects.filter(last_name='Бурканова').count(), 1)

    def test_a_taken_login_is_skipped_rather_than_overwritten(self):
        student = User.objects.create_user(
            username='ivan-bachurin', password='pw',
            first_name='Інший', last_name='Студент', roles=[User.Role.STUDENT])
        self.import_lecturers()
        student.refresh_from_db()
        self.assertEqual(student.roles, {User.Role.STUDENT})
        self.assertEqual(student.first_name, 'Інший')
        self.assertTrue(student.has_usable_password())
        self.assertEqual(
            User.objects.with_role(User.Role.TEACHER).count(),
            len(content.LECTURERS) - 1,
        )

    def test_a_renamed_lecturer_is_updated_in_place(self):
        self.import_lecturers()
        teacher = User.objects.get(username='maryna-bilko')
        teacher.last_name = 'Стара'
        teacher.save(update_fields=['last_name'])
        self.import_lecturers()
        teacher.refresh_from_db()
        self.assertEqual(teacher.last_name, 'Білько')


class RoleSetTests(TestCase):
    """Ролі — набір: людина може мати кілька, і вони змінюються з часом."""

    def make(self, username, *roles):
        return User.objects.create_user(username=username, password='pw', roles=roles)

    def test_one_person_can_manage_and_teach_at_once(self):
        kamysheva = self.make('kamysheva', User.Role.MANAGER, User.Role.TEACHER)
        self.assertTrue(kamysheva.is_manager)
        self.assertTrue(kamysheva.is_teacher)
        self.assertTrue(kamysheva.can_manage_users)
        # і потрапляє в обидві вибірки
        self.assertIn(kamysheva, User.objects.with_role(User.Role.TEACHER))
        self.assertIn(kamysheva, User.objects.with_role(User.Role.MANAGER))

    def test_roles_are_shown_from_the_most_senior_down(self):
        person = self.make('both', User.Role.TEACHER, User.Role.MANAGER)
        self.assertEqual(person.ordered_roles, [User.Role.MANAGER, User.Role.TEACHER])
        self.assertEqual(person.primary_role, User.Role.MANAGER)
        self.assertEqual([label for _, label in person.role_labels], ['Менеджер', 'Викладач'])

    def test_set_roles_replaces_the_whole_set(self):
        person = self.make('changing', User.Role.STUDENT)
        person.set_roles([User.Role.TEACHER, User.Role.MANAGER])
        person.refresh_from_db()
        del person._roles_cache
        self.assertEqual(person.roles, {User.Role.TEACHER, User.Role.MANAGER})

    def test_a_manager_may_not_touch_someone_who_also_manages(self):
        manager = self.make('boss', User.Role.MANAGER)
        admin = self.make('root', User.Role.SUPER_ADMIN)
        teacher = self.make('teach', User.Role.TEACHER)
        dual = self.make('dual', User.Role.MANAGER, User.Role.TEACHER)

        self.assertTrue(manager.can_edit_user(teacher))
        self.assertFalse(manager.can_edit_user(dual))
        self.assertFalse(manager.can_edit_user(manager))
        self.assertTrue(admin.can_edit_user(dual))

    def test_createsuperuser_gets_the_super_admin_role(self):
        """Ролі більше не мають типового значення в колонці — інакше перший
        обліковий запис лишився б без жодного доступу."""
        root = User.objects.create_superuser(username='root2', password='pw', email='')
        self.assertTrue(root.is_super_admin)
        self.assertTrue(root.can_manage_users)

    def test_roles_rank_by_seniority_not_by_the_alphabet_of_their_codes(self):
        """`role_rank` — те, за чим таблиця впорядковує колонку «Роль».

        За кодом ролі сортувати не можна: за абеткою «manager» стало б вище
        за «super_admin».
        """
        people = [
            self.make('c-teacher', User.Role.TEACHER),
            self.make('a-manager', User.Role.MANAGER),
            self.make('b-admin', User.Role.SUPER_ADMIN),
            self.make('d-student', User.Role.STUDENT),
            self.make('e-dual', User.Role.MANAGER, User.Role.TEACHER),
        ]
        by_rank = sorted(people, key=lambda u: (u.role_rank, u.username))
        self.assertEqual(
            [u.username for u in by_rank],
            ['b-admin', 'a-manager', 'e-dual', 'c-teacher', 'd-student'],
        )

    def test_a_manager_cannot_strip_a_role_they_cannot_grant(self):
        """Менеджер, редагуючи колегу-менеджера, не мусить мовчки зняти їй
        роль, якої сам призначити не може."""
        from .forms import UserRoleForm

        manager = self.make('boss2', User.Role.MANAGER)
        dual = self.make('dual2', User.Role.MANAGER, User.Role.TEACHER)
        form = UserRoleForm(
            {'first_name': '', 'last_name': '', 'email': '',
             'is_active': True, 'roles': [User.Role.TEACHER]},
            actor=manager, instance=dual,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(set(form.cleaned_data['roles']),
                         {User.Role.MANAGER, User.Role.TEACHER})


class UserFormViewTests(TestCase):
    """Створення й редагування користувача через сторінку, а не форму напряму."""

    def setUp(self):
        self.manager = User.objects.create_user(
            username='boss3', password='pw', roles=[User.Role.MANAGER])
        self.client.force_login(self.manager)

    def test_the_roles_field_actually_reaches_the_page(self):
        page = self.client.get(reverse('accounts:user_add'))
        self.assertEqual(page.status_code, 200)
        self.assertIn('roles', page.context['form'].fields)
        self.assertIn('name="roles"', page.content.decode())

    def test_a_manager_creates_an_account_with_two_roles_at_once(self):
        response = self.client.post(reverse('accounts:user_add'), {
            'username': 'newbie', 'first_name': 'Нова', 'last_name': 'Людина',
            'email': '', 'password1': 'Str0ng-Pass-9', 'password2': 'Str0ng-Pass-9',
            'roles': [User.Role.TEACHER, User.Role.STUDENT],
        })
        self.assertRedirects(response, reverse('accounts:user_list'))
        created = User.objects.get(username='newbie')
        self.assertEqual(created.roles, {User.Role.TEACHER, User.Role.STUDENT})

    def test_a_manager_cannot_grant_a_role_above_their_own(self):
        response = self.client.post(reverse('accounts:user_add'), {
            'username': 'sneaky', 'first_name': '', 'last_name': '', 'email': '',
            'password1': 'Str0ng-Pass-9', 'password2': 'Str0ng-Pass-9',
            'roles': [User.Role.SUPER_ADMIN],
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='sneaky').exists())

    def test_editing_shows_the_roles_the_account_already_has(self):
        graduate = User.objects.create_user(
            username='alum', password='pw', roles=[User.Role.STUDENT])
        page = self.client.get(reverse('accounts:user_edit', args=[graduate.pk]))
        self.assertEqual(page.context['form'].fields['roles'].initial, [User.Role.STUDENT])

        # випускниця стає викладачкою — додаємо роль, не знімаючи студентську
        self.client.post(reverse('accounts:user_edit', args=[graduate.pk]), {
            'first_name': '', 'last_name': '', 'email': '', 'is_active': 'on',
            'roles': [User.Role.STUDENT, User.Role.TEACHER],
        })
        graduate.refresh_from_db()
        del graduate._roles_cache
        self.assertEqual(graduate.roles, {User.Role.STUDENT, User.Role.TEACHER})


class AccountSettingsTests(TestCase):
    """Свої налаштування: дані, пароль і те, чого тут змінити не можна."""

    def setUp(self):
        self.student = User.objects.create_user(
            username='sasha', password='Str0ng-Pass-9',
            first_name='Саша', last_name='Мороз', roles=[User.Role.STUDENT])
        self.client.force_login(self.student)

    def test_the_page_is_closed_to_guests(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:account'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])

    def test_a_student_updates_their_own_name_and_email(self):
        response = self.client.post(reverse('accounts:account'), {
            'first_name': 'Олександра', 'last_name': 'Мороз',
            'email': 'sasha@example.com',
        })
        self.assertRedirects(response, reverse('accounts:account'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Олександра')
        self.assertEqual(self.student.email, 'sasha@example.com')

    def test_roles_and_the_login_stay_out_of_reach(self):
        """Форма своїх налаштувань не має ні логіна, ні ролей — надіслані
        разом із нею, вони мусять просто ігноруватися."""
        self.client.post(reverse('accounts:account'), {
            'first_name': 'Саша', 'last_name': 'Мороз', 'email': '',
            'username': 'root', 'roles': [User.Role.SUPER_ADMIN],
            'is_active': True,
        })
        self.student.refresh_from_db()
        del self.student._roles_cache
        self.assertEqual(self.student.username, 'sasha')
        self.assertEqual(self.student.roles, {User.Role.STUDENT})

    def test_changing_the_password_needs_the_current_one(self):
        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'wrong-one',
            'new_password1': 'Ev3n-Str0nger-1', 'new_password2': 'Ev3n-Str0nger-1',
        })
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('Str0ng-Pass-9'))

    def test_a_changed_password_works_and_the_session_survives(self):
        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'Str0ng-Pass-9',
            'new_password1': 'Ev3n-Str0nger-1', 'new_password2': 'Ev3n-Str0nger-1',
        })
        self.assertRedirects(response, reverse('accounts:account'))
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('Ev3n-Str0nger-1'))
        # після зміни пароля людина лишається в системі
        self.assertEqual(self.client.get(reverse('accounts:account')).status_code, 200)


class HeaderParser(HTMLParser):
    """Витягує з шапки посилання: адресу, текст і класи.

    Тести шапки раніше звірялися з рядком розмітки (`class="brand" href=...`),
    і будь-який рестайл ламав їх, хоч поведінка лишалася та сама. Дизайн тут
    змінюється часто, тож перевіряємо те, що не залежить від оформлення: куди
    веде посилання і що на ньому написано.
    """

    def __init__(self):
        super().__init__()
        self.in_header = False
        self.links = []          # [{'href': ..., 'text': ..., 'classes': {...}}]
        self.markers = set()     # атрибути-зачіпки, як data-menu-toggle
        self._open = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'header':
            self.in_header = True
        if not self.in_header:
            return
        self.markers |= {name for name, _ in attrs.items() if name.startswith('data-')}
        if tag == 'a':
            self._open = {
                'href': attrs.get('href', ''),
                'classes': set((attrs.get('class') or '').split()),
                'text': '',
            }
            self.links.append(self._open)

    def handle_endtag(self, tag):
        if tag == 'a':
            self._open = None
        if tag == 'header':
            self.in_header = False

    def handle_data(self, data):
        if self._open is not None:
            self._open['text'] += data


def header_of(html):
    parser = HeaderParser()
    parser.feed(html)
    return parser


def link_texts(parser):
    return {link['text'].strip() for link in parser.links if link['text'].strip()}


def hrefs(parser):
    return {link['href'] for link in parser.links}


class PlatformMenuTests(TestCase):
    """Шапка платформи: що в ній є, а чого свідомо немає.

    Перевіряємо адреси, підписи й зачіпки — не класи й не порядок атрибутів:
    оформлення шапки переробляється часто, а домовленості лишаються ті самі.
    """

    def setUp(self):
        self.teacher = User.objects.create_user(
            username='lektor', password='pw', roles=[User.Role.TEACHER])

    def header(self, user=None):
        if user is not None:
            self.client.force_login(user)
        page = self.client.get(reverse('dashboard:home'))
        self.assertEqual(page.status_code, 200)
        return header_of(page.content.decode())

    def test_the_menu_leads_to_the_account_and_back_to_the_public_site(self):
        header = self.header(self.teacher)
        self.assertIn(reverse('accounts:account'), hrefs(header))
        self.assertIn(reverse('core:home'), hrefs(header))
        self.assertIn('Сайт академії', link_texts(header))

    def test_the_sandwich_is_there_and_has_a_name_for_readers(self):
        """Кнопка меню — іконка, тож її сенс несе лише підпис для читачки
        екрана; без нього меню для неї просто безіменне."""
        self.client.force_login(self.teacher)
        body = self.client.get(reverse('dashboard:home')).content.decode()
        self.assertIn('data-menu-toggle', body)
        self.assertIn('Меню акаунту', body)

    def test_there_is_no_cabinet_link_because_the_mark_leads_there(self):
        header = self.header(self.teacher)
        # «Кабінет» лишається назвою сторінки, але не пунктом меню
        self.assertNotIn('Кабінет', link_texts(header))
        brand = [link for link in header.links if 'brand' in link['classes']]
        self.assertEqual(len(brand), 1, 'у шапці має бути рівно один знак-посилання')
        self.assertEqual(brand[0]['href'], reverse('dashboard:home'))

    def test_users_stay_out_of_the_menu_for_those_who_cannot_manage_them(self):
        self.assertNotIn(reverse('accounts:user_list'), hrefs(self.header(self.teacher)))
        manager = User.objects.create_user(
            username='boss4', password='pw', roles=[User.Role.MANAGER])
        self.client.logout()
        self.assertIn(reverse('accounts:user_list'), hrefs(self.header(manager)))


class CardVisibilityTests(TestCase):
    """Кому чия картка «Про мене» видна.

    Керівництво — усі; викладач — свою й своїх студентів; студент — свою й
    своїх викладачів. «Свої» тут — ті, з кем є спільна група.
    """

    @classmethod
    def setUpTestData(cls):
        from schedule.models import Course, Enrollment, Group, GroupSubject, Subject

        cls.manager = User.objects.create_user(
            username='card-mgr', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            username='card-teacher', password='pw', roles=[User.Role.TEACHER])
        cls.other_teacher = User.objects.create_user(
            username='card-teacher-2', password='pw', roles=[User.Role.TEACHER])
        cls.student = User.objects.create_user(
            username='card-student', password='pw', roles=[User.Role.STUDENT])
        cls.other_student = User.objects.create_user(
            username='card-student-2', password='pw', roles=[User.Role.STUDENT])

        today = dt.date.today()
        course = Course.objects.create(name='Майстер дистиляції')
        subject = Subject.objects.create(name='Сенсорика', course=course)
        group = Group.objects.create(
            name='МД-картки', course=course, start_date=today - dt.timedelta(days=30))
        GroupSubject.objects.create(
            group=group, subject=subject, teacher=cls.teacher,
            start_date=today - dt.timedelta(days=30))
        Enrollment.objects.create(
            group=group, student=cls.student, start_date=today - dt.timedelta(days=30))

        # Чужа група — той самий курс, інші люди.
        other_group = Group.objects.create(
            name='МД-чужа', course=course, start_date=today - dt.timedelta(days=30))
        GroupSubject.objects.create(
            group=other_group, subject=subject, teacher=cls.other_teacher,
            start_date=today - dt.timedelta(days=30))
        Enrollment.objects.create(
            group=other_group, student=cls.other_student,
            start_date=today - dt.timedelta(days=30))

    def visible(self, user):
        return set(User.objects.visible_to(user).values_list('username', flat=True))

    def test_management_sees_every_card(self):
        self.assertEqual(self.visible(self.manager), set(
            User.objects.values_list('username', flat=True)))

    def test_a_teacher_sees_their_students_and_nobody_elses(self):
        self.assertEqual(
            self.visible(self.teacher), {'card-teacher', 'card-student'})

    def test_a_student_sees_their_teachers_and_nobody_elses(self):
        self.assertEqual(
            self.visible(self.student), {'card-student', 'card-teacher'})

    def test_two_roles_add_up_rather_than_replace_each_other(self):
        """Викладачка, яка сама тут навчалася, не має втратити ні своїх
        студентів, ні викладачів своєї групи."""
        self.teacher.add_role(User.Role.STUDENT)
        from schedule.models import Enrollment, Group

        Enrollment.objects.create(
            group=Group.objects.get(name='МД-чужа'), student=self.teacher,
            start_date=dt.date.today() - dt.timedelta(days=10))
        self.assertEqual(
            self.visible(self.teacher),
            {'card-teacher', 'card-student', 'card-teacher-2'})

    def test_a_finished_group_does_not_take_the_cards_away(self):
        from schedule.models import Group

        group = Group.objects.get(name='МД-картки')
        group.end_date = dt.date.today() - dt.timedelta(days=1)
        group.save(update_fields=['end_date'])
        self.assertIn('card-student', self.visible(self.teacher))

    def test_a_hidden_card_is_a_404_not_a_redirect(self):
        self.client.force_login(self.teacher)
        hidden = self.client.get(
            reverse('accounts:person_detail', args=[self.other_student.pk]))
        self.assertEqual(hidden.status_code, 404)
        own = self.client.get(
            reverse('accounts:person_detail', args=[self.teacher.pk]))
        self.assertEqual(own.status_code, 200)

    def test_the_card_list_shows_exactly_what_is_visible(self):
        self.client.force_login(self.student)
        page = self.client.get(reverse('accounts:person_list'))
        self.assertEqual(
            {p.username for p in page.context['people']},
            {'card-student', 'card-teacher'})

    def test_guests_see_no_cards_at_all(self):
        response = self.client.get(reverse('accounts:person_list'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.visible(AnonymousUser()), set())


class OwnCardTests(TestCase):
    """Своя картка: що людина про себе пише й чого змінити не може."""

    def setUp(self):
        self.person = User.objects.create_user(
            username='pysar', password='Str0ng-Pass-9',
            first_name='Оксана', last_name='Вітряк', roles=[User.Role.TEACHER])
        self.client.force_login(self.person)

    def card_data(self, **extra):
        data = {
            'last_name': 'Вітряк', 'first_name': 'Оксана',
            'patronymic': 'Петрівна', 'email': 'o@example.com',
            'about': 'Аудиторка систем безпечності.',
            'education': 'НУХТ, к.т.н.',
            'interests': 'ISO 22000, HACCP.',
            'experience': 'Доцент кафедри технології ресторанного господарства.',
        }
        data.update(extra)
        return data

    def test_the_card_is_filled_in_from_ones_own_settings(self):
        response = self.client.post(reverse('accounts:account'), self.card_data())
        self.assertRedirects(response, reverse('accounts:account'))
        self.person.refresh_from_db()
        self.assertEqual(self.person.patronymic, 'Петрівна')
        self.assertEqual(self.person.education, 'НУХТ, к.т.н.')
        self.assertEqual(
            [label for label, _ in self.person.card_facts],
            ['Про мене', 'Освіта', 'Інтереси', 'Робочий досвід'])

    def test_the_full_name_puts_the_patronymic_last(self):
        self.client.post(reverse('accounts:account'), self.card_data())
        self.person.refresh_from_db()
        self.assertEqual(self.person.display_name, 'Вітряк Оксана Петрівна')

    def test_without_a_patronymic_the_name_is_just_the_two_parts(self):
        self.assertEqual(self.person.display_name, 'Вітряк Оксана')

    def test_a_photo_reaches_the_card(self):
        photo = SimpleUploadedFile('me.png', ONE_PIXEL_PNG, content_type='image/png')
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.client.post(reverse('accounts:account'), self.card_data(photo=photo))
                self.person.refresh_from_db()
                self.assertTrue(self.person.photo)
                self.assertTrue(os.path.exists(self.person.photo.path))

    def test_a_new_portrait_does_not_leave_the_old_file_behind(self):
        with tempfile.TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                for name in ('first.png', 'second.png'):
                    self.client.post(reverse('accounts:account'), self.card_data(
                        photo=SimpleUploadedFile(name, ONE_PIXEL_PNG, content_type='image/png')))
                self.person.refresh_from_db()
                self.assertEqual(os.listdir(os.path.join(media, 'profiles')),
                                 [os.path.basename(self.person.photo.name)])

    def test_roles_and_the_login_stay_out_of_the_card_form(self):
        self.client.post(reverse('accounts:account'), self.card_data(
            username='root', roles=[User.Role.SUPER_ADMIN], is_active=True))
        self.person.refresh_from_db()
        del self.person._roles_cache
        self.assertEqual(self.person.username, 'pysar')
        self.assertEqual(self.person.roles, {User.Role.TEACHER})

    def test_nobody_edits_somebody_elses_card(self):
        """Менеджерська форма правує обліковий запис, а не текст про людину —
        «Про мене» лишається за самою людиною."""
        from .forms import UserRoleForm

        self.assertNotIn('about', UserRoleForm.base_fields)
        self.assertNotIn('education', UserRoleForm.base_fields)


class LecturerCardImportTests(TestCase):
    """Фото й біографії лекторів зі старого сайту — у картки викладачів."""

    def import_cards(self, **options):
        # `--local` бере ті самі фото з `static/img/lecturers/`, тож тест не
        # залежить від того, чи відповідає сайт.
        call_command('import_lecturer_cards', local=True, verbosity=0, **options)

    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        call_command('import_lecturers', verbosity=0)

    def test_every_lecturer_ends_up_with_a_photo_and_a_bio(self):
        self.import_cards()
        teachers = User.objects.with_role(User.Role.TEACHER)
        self.assertEqual(teachers.exclude(photo='').count(), len(content.LECTURERS))
        for teacher in teachers:
            with self.subTest(username=teacher.username):
                self.assertTrue(os.path.exists(teacher.photo.path))
                self.assertTrue(teacher.about)

    def test_the_bio_from_the_site_lands_in_the_card(self):
        self.import_cards()
        founder = User.objects.get(username='kateryna-kamysheva')
        self.assertIn('Асоціації крафтових дистилерів', founder.about)

    def test_what_a_person_wrote_themselves_is_not_overwritten(self):
        self.import_cards()
        teacher = User.objects.get(username='ivan-bachurin')
        teacher.about = 'Свій текст.'
        teacher.save(update_fields=['about'])
        self.import_cards()
        teacher.refresh_from_db()
        self.assertEqual(teacher.about, 'Свій текст.')

    def test_replace_overwrites_and_leaves_no_second_file_behind(self):
        self.import_cards()
        teacher = User.objects.get(username='ivan-bachurin')
        first = teacher.photo.name
        self.import_cards(replace=True)
        teacher.refresh_from_db()
        self.assertEqual(teacher.photo.name, first)
        self.assertEqual(len(os.listdir(os.path.join(self.media.name, 'profiles'))),
                         len(content.LECTURERS))

    def test_dry_run_writes_nothing(self):
        self.import_cards(dry_run=True)
        self.assertEqual(
            User.objects.with_role(User.Role.TEACHER).exclude(photo='').count(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.media.name, 'profiles')))

    def test_a_stranger_under_the_slug_login_keeps_their_own_card(self):
        """Логін-слаг могла зайняти інша людина — фото лектора в її картці
        не має з'явитися."""
        stranger = User.objects.get(username='ivan-bachurin')
        stranger.first_name, stranger.last_name = 'Інший', 'Студент'
        stranger.set_roles([User.Role.STUDENT])
        stranger.about = 'Я тут навчаюся.'
        stranger.save(update_fields=['first_name', 'last_name', 'about'])
        self.import_cards()
        stranger.refresh_from_db()
        self.assertFalse(stranger.photo)
        self.assertEqual(stranger.about, 'Я тут навчаюся.')

    def test_a_lecturer_who_only_manages_still_gets_her_card(self):
        art_director = User.objects.get(username='olga-burkanova')
        art_director.set_roles([User.Role.MANAGER])
        self.import_cards(replace=True)
        art_director.refresh_from_db()
        del art_director._roles_cache
        self.assertTrue(art_director.photo)
        self.assertIn('Арт-директорка', art_director.about)
        self.assertEqual(art_director.roles, {User.Role.MANAGER})


class MergeUsersTests(TestCase):
    """Зведення двох записів однієї людини (`manage.py merge_users`)."""

    @classmethod
    def setUpTestData(cls):
        from schedule.models import Course, Group, Subject

        cls.course = Course.objects.create(name='Майстер дистиляції')
        cls.subject = Subject.objects.create(name='Бренд. Дизайн. Етикетка', course=cls.course)
        cls.group = Group.objects.create(
            name='МД-звід', course=cls.course, start_date=dt.date.today() - dt.timedelta(days=30))

    def setUp(self):
        # Робочий акаунт людини й той, що завівся імпортом під дівочим прізвищем.
        self.keeper = User.objects.create_user(
            username='manager', password='pw', first_name='Катерина',
            last_name='Камишева', roles=[User.Role.MANAGER])
        self.duplicate = User.objects.create_user(
            username='kateryna-lavrenova', password='pw', first_name='Катерина',
            last_name='Лавренова', roles=[User.Role.TEACHER],
            about='Голова Асоціації крафтових дистилерів.')

    def merge(self, **options):
        call_command('merge_users', 'manager', 'kateryna-lavrenova', verbosity=0, **options)

    def test_the_duplicate_is_gone_and_the_working_login_survives(self):
        self.merge()
        self.assertFalse(User.objects.filter(username='kateryna-lavrenova').exists())
        self.keeper.refresh_from_db()
        self.assertEqual(self.keeper.last_name, 'Камишева')

    def test_roles_add_up(self):
        self.merge()
        self.keeper.refresh_from_db()
        del self.keeper._roles_cache
        self.assertEqual(self.keeper.roles, {User.Role.MANAGER, User.Role.TEACHER})

    def test_an_empty_field_is_filled_from_the_duplicate_card(self):
        self.merge()
        self.keeper.refresh_from_db()
        self.assertIn('Асоціації крафтових дистилерів', self.keeper.about)

    def test_what_the_person_already_wrote_wins(self):
        self.keeper.about = 'Свій текст.'
        self.keeper.save(update_fields=['about'])
        self.merge()
        self.keeper.refresh_from_db()
        self.assertEqual(self.keeper.about, 'Свій текст.')

    def test_the_work_of_the_duplicate_moves_over(self):
        from schedule.models import Enrollment, GroupSubject, ScheduleEntry

        start = dt.date.today() - dt.timedelta(days=30)
        self.subject.teachers.add(self.duplicate)
        GroupSubject.objects.create(
            group=self.group, subject=self.subject, teacher=self.duplicate, start_date=start)
        Enrollment.objects.create(group=self.group, student=self.duplicate, start_date=start)
        entry = ScheduleEntry.objects.create(
            group=self.group, date=dt.date.today(), start_time=dt.time(10),
            end_time=dt.time(12), source=ScheduleEntry.Source.TEACHER,
            created_by=self.duplicate, reviewed_by=self.duplicate)

        self.merge()
        self.assertEqual(list(self.keeper.subjects.values_list('name', flat=True)),
                         ['Бренд. Дизайн. Етикетка'])
        self.assertEqual(self.keeper.group_subjects.count(), 1)
        self.assertEqual(self.keeper.enrollments.count(), 1)
        entry.refresh_from_db()
        self.assertEqual(entry.created_by, self.keeper)
        self.assertEqual(entry.reviewed_by, self.keeper)

    def test_the_same_enrollment_recorded_twice_is_not_duplicated(self):
        """Обидва записи в тій самій групі з тим самим початком — це та сама
        подія, тож зайвий прибирається, а не ламає унікальність."""
        from schedule.models import Enrollment

        start = dt.date.today() - dt.timedelta(days=30)
        Enrollment.objects.create(group=self.group, student=self.keeper, start_date=start)
        Enrollment.objects.create(group=self.group, student=self.duplicate, start_date=start)
        self.merge()
        self.assertEqual(Enrollment.objects.filter(group=self.group).count(), 1)
        self.assertEqual(self.keeper.enrollments.count(), 1)

    def test_a_subject_taught_by_both_does_not_double(self):
        self.subject.teachers.add(self.keeper, self.duplicate)
        self.merge()
        self.assertEqual(self.subject.teachers.count(), 1)

    def test_nobody_elses_roles_are_touched(self):
        bystander = User.objects.create_user(
            username='bystander', password='pw', roles=[User.Role.TEACHER])
        self.merge()
        bystander.refresh_from_db()
        del bystander._roles_cache
        self.assertEqual(bystander.roles, {User.Role.TEACHER})

    def test_dry_run_changes_nothing(self):
        self.merge(dry_run=True)
        self.assertTrue(User.objects.filter(username='kateryna-lavrenova').exists())
        self.keeper.refresh_from_db()
        del self.keeper._roles_cache
        self.assertEqual(self.keeper.roles, {User.Role.MANAGER})
        self.assertEqual(self.keeper.about, '')

    def test_an_unknown_login_is_an_error_rather_than_a_silent_no_op(self):
        with self.assertRaises(CommandError):
            call_command('merge_users', 'manager', 'nobody', verbosity=0)
        with self.assertRaises(CommandError):
            call_command('merge_users', 'manager', 'manager', verbosity=0)
