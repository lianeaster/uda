import datetime as dt

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schedule.models import Course, Enrollment, Group, GroupSubject, Subject

TODAY = dt.date.today()
MONTH_AGO = TODAY - dt.timedelta(days=30)


class RoleVisibilityTests(TestCase):
    """Each role's dashboard tiles, and the scoping of the pages behind them."""

    @classmethod
    def setUpTestData(cls):
        def user(username, *roles):
            return User.objects.create_user(username=username, password='pw', roles=roles)

        cls.admin = user('admin', User.Role.SUPER_ADMIN)
        cls.manager = user('manager', User.Role.MANAGER)
        cls.teacher = user('teacher', User.Role.TEACHER)
        cls.other_teacher = user('other', User.Role.TEACHER)
        cls.student = user('student', User.Role.STUDENT)
        cls.other_student = user('outsider', User.Role.STUDENT)

        cls.course = Course.objects.create(name='Майстер дистиляції')
        cls.other_course = Course.objects.create(name='Зернові дистиляти')
        cls.subject = Subject.objects.create(name='Сенсорика', course=cls.course)
        cls.other_subject_of_course = Subject.objects.create(
            name='Ферментація', course=cls.course)
        cls.other_subject = Subject.objects.create(name='Солод', course=cls.other_course)

        cls.own_group = Group.objects.create(name='МД-1', course=cls.course, start_date=MONTH_AGO)
        cls.foreign_group = Group.objects.create(name='ЗД-1', course=cls.other_course, start_date=MONTH_AGO)

        GroupSubject.objects.create(
            group=cls.own_group, subject=cls.subject, teacher=cls.teacher, start_date=MONTH_AGO)
        GroupSubject.objects.create(
            group=cls.foreign_group, subject=cls.other_subject,
            teacher=cls.other_teacher, start_date=MONTH_AGO)

        Enrollment.objects.create(group=cls.own_group, student=cls.student, start_date=MONTH_AGO)
        Enrollment.objects.create(group=cls.foreign_group, student=cls.other_student, start_date=MONTH_AGO)

    def dashboard(self, who):
        self.client.force_login(who)
        return self.client.get(reverse('dashboard:home'))

    # --- tiles ---------------------------------------------------------

    def test_manager_roles_see_all_six_tiles(self):
        for who in (self.admin, self.manager):
            with self.subTest(user=who.username):
                page = self.dashboard(who).content.decode()
                for tile in ('Розклад', 'Групи', 'Викладачі', 'Студенти', 'Курси', 'Предмети'):
                    self.assertIn(f'<h3>{tile}</h3>', page)

    def test_teacher_has_every_tile_except_teachers(self):
        page = self.dashboard(self.teacher).content.decode()
        self.assertNotIn('<h3>Викладачі</h3>', page)
        for tile in ('Розклад', 'Мої групи', 'Мої студенти', 'Курси', 'Мої предмети'):
            self.assertIn(f'<h3>{tile}</h3>', page)

    def test_tile_counts_are_scoped_to_the_role(self):
        admin_ctx = self.dashboard(self.admin).context
        self.assertEqual(admin_ctx['group_total'], 2)
        self.assertEqual(admin_ctx['student_count'], 2)
        self.assertEqual(admin_ctx['teacher_count'], 2)

        teacher_ctx = self.dashboard(self.teacher).context
        self.assertEqual(teacher_ctx['group_total'], 1)
        self.assertEqual(teacher_ctx['student_count'], 1)
        self.assertIsNone(teacher_ctx.get('teacher_count'))
        # courses are a flat catalogue, the same number for everyone
        self.assertEqual(teacher_ctx['course_count'], admin_ctx['course_count'])
        # subjects are the catalogue too, but the teacher's tile counts their own
        self.subject.teachers.add(self.teacher)
        teacher_ctx = self.dashboard(self.teacher).context
        self.assertEqual(teacher_ctx['subject_count'], 1)
        self.assertEqual(teacher_ctx['subject_total'], admin_ctx['subject_count'])

    # --- groups --------------------------------------------------------

    def test_manager_sees_every_group_and_teacher_only_their_own(self):
        self.client.force_login(self.manager)
        self.assertEqual(
            {g.name for g in self.client.get(reverse('schedule:group_list')).context['groups']},
            {'МД-1', 'ЗД-1'})

        self.client.force_login(self.teacher)
        self.assertEqual(
            {g.name for g in self.client.get(reverse('schedule:group_list')).context['groups']},
            {'МД-1'})

    def test_teacher_cannot_open_a_group_they_do_not_teach_in(self):
        self.client.force_login(self.teacher)
        own = self.client.get(reverse('schedule:group_detail', args=[self.own_group.pk]))
        foreign = self.client.get(reverse('schedule:group_detail', args=[self.foreign_group.pk]))
        self.assertEqual(own.status_code, 200)
        self.assertEqual(foreign.status_code, 404)

    def test_student_sees_only_the_groups_they_are_enrolled_in(self):
        self.client.force_login(self.student)
        groups = self.client.get(reverse('schedule:group_list')).context['groups']
        self.assertEqual({g.name for g in groups}, {'МД-1'})

    def test_finished_group_drops_out_of_the_active_scope_but_stays_in_history(self):
        self.own_group.end_date = TODAY - dt.timedelta(days=1)
        self.own_group.save()
        self.client.force_login(self.teacher)
        url = reverse('schedule:group_list')
        self.assertEqual(len(self.client.get(url).context['groups']), 0)
        self.assertEqual(len(self.client.get(url, {'scope': 'all'}).context['groups']), 1)

    # --- students ------------------------------------------------------

    def test_teacher_sees_only_students_of_their_own_groups(self):
        self.client.force_login(self.teacher)
        rows = self.client.get(reverse('schedule:student_list')).context['enrollments']
        self.assertEqual({e.student.username for e in rows}, {'student'})

        self.client.force_login(self.manager)
        rows = self.client.get(reverse('schedule:student_list')).context['enrollments']
        self.assertEqual({e.student.username for e in rows}, {'student', 'outsider'})

    # --- catalogue -----------------------------------------------------

    def test_teacher_sees_the_whole_catalogue_but_cannot_change_it(self):
        self.client.force_login(self.teacher)
        for name, add_url in (('course_list', 'schedule:course_add'),
                              ('subject_list', 'schedule:subject_add')):
            with self.subTest(page=name):
                page = self.client.get(reverse(f'schedule:{name}'))
                self.assertEqual(page.status_code, 200)
                self.assertNotIn(reverse(add_url), page.content.decode())

        self.assertEqual(
            len(self.client.get(reverse('schedule:course_list')).context['courses']),
            Course.objects.count())
        subjects = reverse('schedule:subject_list')
        self.assertEqual(
            len(self.client.get(subjects, {'scope': 'all'}).context['subjects']),
            Subject.objects.count())

    def test_subject_list_opens_on_the_teachers_own_subjects(self):
        self.subject.teachers.add(self.teacher)
        self.client.force_login(self.teacher)
        url = reverse('schedule:subject_list')

        mine = self.client.get(url)
        self.assertEqual([s.name for s in mine.context['subjects']], ['Сенсорика'])
        self.assertEqual(mine.context['scope'], 'mine')
        self.assertIn('Мої предмети', mine.content.decode())

        # межа тут — лише фільтр: каталог відкритий увесь
        every = self.client.get(url, {'scope': 'all'})
        self.assertEqual(len(every.context['subjects']), Subject.objects.count())

    def test_managers_see_the_catalogue_unfiltered_with_no_scope_switch(self):
        self.subject.teachers.add(self.teacher)
        self.client.force_login(self.manager)
        page = self.client.get(reverse('schedule:subject_list'))
        self.assertEqual(len(page.context['subjects']), Subject.objects.count())
        self.assertFalse(page.context['is_teacher'])
        self.assertIsNone(page.context.get('scope'))

    def test_super_admin_group_pages_render_with_their_admin_links(self):
        self.client.force_login(self.admin)
        listing = self.client.get(reverse('schedule:group_list'))
        detail = self.client.get(reverse('schedule:group_detail', args=[self.own_group.pk]))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(reverse('admin:schedule_group_add'), listing.content.decode())
        self.assertIn(
            reverse('admin:schedule_group_change', args=[self.own_group.pk]),
            detail.content.decode())

    def make_graduate_turned_teacher(self, username='graduate'):
        """Провчилась, випустилась — і згодом прийшла в штат викладачкою.

        Роль викладача саме ДОДАЄТЬСЯ: студенткою вона бути не перестала,
        просто її група вже закінчила навчання.
        """
        person = User.objects.create_user(
            username=username, password='pw', roles=[User.Role.STUDENT])
        record = Enrollment.objects.create(
            group=self.own_group, student=person,
            start_date=MONTH_AGO, end_date=TODAY - dt.timedelta(days=1))
        person.add_role(User.Role.TEACHER)
        teaches_in = Group.objects.create(
            name='МД-9', course=self.course, start_date=MONTH_AGO)
        GroupSubject.objects.create(
            group=teaches_in, subject=self.other_subject_of_course,
            teacher=person, start_date=MONTH_AGO)
        return User.objects.get(pk=person.pk), record

    def test_becoming_a_teacher_adds_a_role_it_does_not_replace_one(self):
        person, record = self.make_graduate_turned_teacher()
        self.assertEqual(person.roles, {User.Role.STUDENT, User.Role.TEACHER})

        record.refresh_from_db()
        record.full_clean()          # історія не стає недійсною
        self.assertIn(person, self.own_group.students)

    def test_a_graduate_who_teaches_keeps_access_to_their_own_group(self):
        """Додана роль викладача не має віднімати доступ до того, де вчилася."""
        person, _ = self.make_graduate_turned_teacher()
        self.client.force_login(person)

        listing = self.client.get(reverse('schedule:group_list'), {'scope': 'all'})
        self.assertEqual(
            {g.name for g in listing.context['groups']},
            {'МД-1', 'МД-9'},        # де вчилася + де викладає
        )

        alma = self.client.get(reverse('schedule:group_detail', args=[self.own_group.pk]))
        self.assertEqual(alma.status_code, 200)

    def test_the_list_says_in_which_capacity_she_is_in_each_group(self):
        person, _ = self.make_graduate_turned_teacher()
        self.client.force_login(person)
        groups = {
            g.name: (g.i_teach, g.i_study)
            for g in self.client.get(
                reverse('schedule:group_list'), {'scope': 'all'}).context['groups']
        }
        self.assertEqual(groups['МД-1'], (False, True))     # тут навчалася
        self.assertEqual(groups['МД-9'], (True, False))     # тут викладає

    def test_a_plain_student_reaches_their_group_from_the_dashboard(self):
        response = self.dashboard(self.student)
        self.assertTrue(response.context['student_tiles'])
        self.assertEqual(response.context['group_total'], 1)
        self.assertIn('<h3>Моє навчання</h3>', response.content.decode())

    def test_someone_who_manages_and_teaches_gets_both_sets_of_tiles(self):
        dual = User.objects.create_user(
            username='dual', password='pw',
            roles=[User.Role.MANAGER, User.Role.TEACHER])
        GroupSubject.objects.create(
            group=self.own_group, subject=self.other_subject_of_course,
            teacher=dual, start_date=MONTH_AGO)

        response = self.dashboard(dual)
        page = response.content.decode()
        self.assertIn('<h3>Викладачі</h3>', page)     # керує
        self.assertIn('<h3>Групи</h3>', page)
        # керування головніше: тайли рахують усю Академію, не лише її групи
        self.assertFalse(response.context['own_scope'])
        self.assertEqual(response.context['group_total'], 2)
        self.assertNotIn('<h3>Мої групи</h3>', page)

    def test_a_managing_teacher_can_narrow_groups_to_where_they_teach(self):
        dual = User.objects.create_user(
            username='dual2', password='pw',
            roles=[User.Role.MANAGER, User.Role.TEACHER])
        GroupSubject.objects.create(
            group=self.own_group, subject=self.other_subject_of_course,
            teacher=dual, start_date=MONTH_AGO)
        self.client.force_login(dual)
        url = reverse('schedule:group_list')

        everything = self.client.get(url)
        self.assertEqual({g.name for g in everything.context['groups']}, {'МД-1', 'ЗД-1'})
        self.assertTrue(everything.context['can_switch_who'])

        mine = self.client.get(url, {'who': 'mine'})
        self.assertEqual({g.name for g in mine.context['groups']}, {'МД-1'})

    def test_teacher_is_still_locked_out_of_user_management(self):
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('accounts:user_list'))
        self.assertRedirects(page, reverse('dashboard:home'))


class EveryPageRendersForEveryRoleTests(TestCase):
    """Кожна сторінка платформи відкривається кожною роллю без винятку.

    Саме цього бракувало: `limit_choices_to={'role': ...}` на
    `ScheduleEntry.teacher` лишився після переходу на набір ролей і валив
    /schedule/ для менеджера — але жоден тест ту сторінку менеджером не
    відкривав. Тут важливо не «що видно», а «нічого не падає».
    """

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name='Майстер дистиляції')
        cls.subject = Subject.objects.create(name='Сенсорика', course=cls.course)
        cls.group = Group.objects.create(
            name='МД-1', course=cls.course, start_date=MONTH_AGO)

        cls.people = {
            'super_admin': [User.Role.SUPER_ADMIN],
            'manager': [User.Role.MANAGER],
            'teacher': [User.Role.TEACHER],
            'student': [User.Role.STUDENT],
            'manager_teacher': [User.Role.MANAGER, User.Role.TEACHER],
            'student_teacher': [User.Role.STUDENT, User.Role.TEACHER],
        }
        cls.users = {
            name: User.objects.create_user(username=name, password='pw', roles=roles)
            for name, roles in cls.people.items()
        }
        # один предмет у групі веде рівно один викладач, тож кожному свій
        for index, name in enumerate(('teacher', 'manager_teacher', 'student_teacher')):
            GroupSubject.objects.create(
                group=cls.group,
                subject=Subject.objects.create(
                    name=f'Предмет {index}', course=cls.course),
                teacher=cls.users[name], start_date=MONTH_AGO)
        for name in ('student', 'student_teacher'):
            Enrollment.objects.create(
                group=cls.group, student=cls.users[name], start_date=MONTH_AGO)

    def urls(self):
        return [
            reverse('dashboard:home'),
            reverse('schedule:home'),
            reverse('schedule:proposal_list'),
            reverse('schedule:group_list'),
            reverse('schedule:group_list') + '?scope=all&who=all',
            reverse('schedule:group_detail', args=[self.group.pk]),
            reverse('schedule:student_list'),
            reverse('schedule:student_list') + '?scope=all',
            reverse('schedule:course_list'),
            reverse('schedule:course_add'),
            reverse('schedule:subject_list'),
            reverse('schedule:subject_list') + '?scope=all',
            reverse('schedule:subject_add'),
            reverse('accounts:user_list'),
            reverse('accounts:user_list') + '?sort=role&dir=desc',
            reverse('accounts:user_add'),
            reverse('accounts:user_edit', args=[self.users['teacher'].pk]),
        ]

    def test_no_page_raises_for_any_role(self):
        for name, person in self.users.items():
            self.client.force_login(person)
            for url in self.urls():
                with self.subTest(role=name, url=url):
                    response = self.client.get(url, follow=True)
                    self.assertEqual(
                        response.status_code, 200,
                        f'{url} під {name} віддав {response.status_code}')

    def test_every_table_on_the_platform_is_sortable_and_filterable(self):
        """Правило: жодної таблиці без сортування й фільтрації по колонках.

        Перевіряємо саме розмітку, бо поведінку дає один спільний скрипт
        (`static/js/table.js`) — варто новій таблиці з'явитися без `data-table`,
        і вона мовчки лишиться без обох.
        """
        self.client.force_login(self.users['super_admin'])
        for url in self.urls():
            page = self.client.get(url, follow=True).content.decode()
            opened = page.count('<table')
            if not opened:
                continue
            with self.subTest(url=url):
                self.assertEqual(
                    page.count('<table data-table'), opened,
                    f'{url}: не всі таблиці мають data-table')

    def test_columns_that_do_not_sort_by_their_own_text_say_what_to_sort_by(self):
        """Дати й номери предметів як текст упорядкувалися б неправильно."""
        self.client.force_login(self.users['super_admin'])

        groups = self.client.get(reverse('schedule:group_list')).content.decode()
        self.assertIn(f'data-sort="{MONTH_AGO.isoformat()}"', groups)

        subjects = self.client.get(
            reverse('schedule:subject_list')).content.decode()
        self.assertIn(f'data-sort="{self.subject.position}"', subjects)

        users = self.client.get(reverse('accounts:user_list')).content.decode()
        self.assertIn('data-sort="0"', users)      # супер-адмін — найстарша роль

    def test_managing_and_teaching_adds_up_in_schedule_permissions(self):
        """Права складаються: і бронювання Академії, і власна пропозиція."""
        from schedule.models import ScheduleEntry
        from schedule.services import can_modify

        dual = self.users['manager_teacher']
        lesson = GroupSubject.objects.get(teacher=dual)

        academy_booking = ScheduleEntry(
            group=self.group, date=TODAY,
            start_time=dt.time(10), end_time=dt.time(12),
            source=ScheduleEntry.Source.ACADEMY,
            status=ScheduleEntry.Status.ACCEPTED, created_by=dual)
        own_proposal = ScheduleEntry(
            group=self.group, group_subject=lesson, date=TODAY,
            start_time=dt.time(12), end_time=dt.time(14),
            source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=dual)
        someone_elses = ScheduleEntry(
            group=self.group, date=TODAY,
            start_time=dt.time(14), end_time=dt.time(16),
            source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED,
            created_by=self.users['teacher'])

        self.assertTrue(can_modify(academy_booking, dual))   # як менеджерка
        self.assertTrue(can_modify(own_proposal, dual))      # як викладачка
        self.assertFalse(can_modify(someone_elses, dual))    # чужа пропозиція

        # чистий викладач менеджерського боку не отримує
        self.assertFalse(can_modify(academy_booking, self.users['teacher']))

    def test_the_booking_form_offers_only_this_groups_subjects(self):
        """Викладача тут більше не обирають — він випливає з предмета."""
        self.client.force_login(self.users['manager'])
        form = self.client.get(reverse('schedule:home')).context['form']
        self.assertNotIn('teacher', form.fields)
        self.assertNotIn('course', form.fields)
        self.assertEqual(
            set(form.fields['group_subject'].queryset),
            set(self.group.group_subjects.all()),
        )
        self.assertFalse(form.fields['group_subject'].required)

    def test_a_teacher_may_only_propose_for_their_own_subject(self):
        teacher = self.users['teacher']
        self.client.force_login(teacher)
        form = self.client.get(reverse('schedule:home')).context['form']
        self.assertTrue(form.fields['group_subject'].required)
        self.assertEqual(
            {link.teacher for link in form.fields['group_subject'].queryset},
            {teacher},
        )
