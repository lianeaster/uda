from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core import content

from .models import User


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

    def test_logins_come_from_the_photo_slug_without_the_bc_prefix(self):
        self.import_lecturers()
        self.assertTrue(User.objects.filter(username='olexandr-ryabtsev').exists())
        self.assertTrue(User.objects.filter(username='kateryna-lavrenova').exists())
        self.assertFalse(User.objects.filter(username__startswith='bc-').exists())

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
