from django.core.management import call_command
from django.test import TestCase

from accounts.models import User

from . import programs
from .models import Course, CourseSubject, Module, Subject
from .testing import make_subject


class ImportProgramTests(TestCase):
    """Предмети програми курсу та їхні викладачі з графіка 8-ї групи."""

    def import_program(self, **options):
        call_command('import_program', verbosity=0, **options)

    def test_every_numbered_item_becomes_a_subject_of_the_course(self):
        self.import_program()
        course = Course.objects.get(name=programs.COURSE)
        expected = list(programs.subjects())
        self.assertEqual(course.subjects.count(), len(expected))
        for position, code, name, _module, _lecturers, _hours in expected:
            with self.subTest(code=code):
                link = CourseSubject.objects.get(subject__name=name)
                self.assertEqual(link.course, course)
                self.assertEqual(link.code, code)
                self.assertEqual(link.position, position)

    def test_subjects_keep_the_order_of_the_programme_not_the_alphabet(self):
        self.import_program()
        codes = list(
            Course.objects.get(name=programs.COURSE).program.values_list('code', flat=True)
        )
        self.assertEqual(codes, [code for _, code, *_ in programs.subjects()])
        # за абеткою «10.1» стояло б перед «2.1» — саме тому є `position`
        self.assertLess(codes.index('2.1'), codes.index('10.1'))

    def test_teachers_are_linked_to_what_the_schedule_says_they_teach(self):
        self.import_program()
        bachurin = User.objects.get(username='ivan-bachurin')
        self.assertEqual(
            sorted(bachurin.subjects.values_list('course_links__code', flat=True)),
            ['2.2', '2.3', '2.4', '2.5'],
        )
        # один предмет може вести двоє — «8.2 Витримка в бочці»
        cask = Subject.objects.get(name='Витримка в бочці')
        self.assertEqual(
            set(cask.teachers.values_list('username', flat=True)),
            {'yury-kepkanov', 'maryna-bilko'},
        )

    def test_spelling_variants_in_the_schedule_resolve_to_one_person(self):
        self.import_program()
        # «Білько М.В» / «Білько М.В.» / «Билько М.» — та сама людина
        bilko = User.objects.get(username='maryna-bilko')
        self.assertEqual(
            sorted(bilko.subjects.values_list('course_links__code', flat=True)),
            ['3.3', '3.6', '7.3', '8.2'],
        )
        self.assertEqual(User.objects.filter(last_name__in=['Білько', 'Билько']).count(), 1)

    def test_lecturers_absent_from_the_platform_are_created_without_a_password(self):
        self.import_program()
        newcomer = User.objects.get(username='natasha-kravchuk')
        self.assertEqual(newcomer.roles, {User.Role.TEACHER})
        self.assertEqual(newcomer.get_full_name(), 'Наташа Кравчук')
        self.assertFalse(newcomer.has_usable_password())

    def test_a_manager_named_as_a_lecturer_keeps_their_role_and_gets_no_subjects(self):
        manager = User.objects.create_user(
            username='manager', password='pw', first_name='Катерина',
            last_name='Камишева', roles=[User.Role.MANAGER])
        self.import_program()
        manager.refresh_from_db()
        self.assertEqual(manager.roles, {User.Role.MANAGER})
        self.assertFalse(manager.subjects.exists())
        # її предмети лишаються без викладача, а не дістаються комусь іншому
        self.assertFalse(Subject.objects.get(name='Маркетингова складова').teachers.exists())

    def test_running_twice_changes_nothing(self):
        self.import_program()
        def snapshot():
            return {
                (link.subject_id, link.code, link.position,
                 tuple(sorted(link.subject.teachers.values_list('pk', flat=True))))
                for link in CourseSubject.objects.select_related('subject')
            }
        before = snapshot()
        self.import_program()
        after = snapshot()
        self.assertEqual(after, before)

    def test_dry_run_writes_nothing(self):
        self.import_program(dry_run=True)
        self.assertEqual(Subject.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)

    def test_subjects_of_the_course_outside_the_programme_are_left_alone(self):
        course = Course.objects.create(name=programs.COURSE)
        stray = make_subject('Старий предмет', course=course, position=999)
        self.import_program()
        link = CourseSubject.objects.get(subject=stray)
        self.assertEqual(link.course, course)
        self.assertEqual(link.position, 999)


import datetime as dt

from django.urls import reverse

from .models import Enrollment, Group, GroupSubject, ScheduleEntry
from .services import can_modify, can_review

TODAY = dt.date.today()
MONTH_AGO = TODAY - dt.timedelta(days=30)


class ScheduleFlowTests(TestCase):
    """Колір за походженням запису, і шлях пропозиції від викладача."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            username='mgr', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            username='tchr', password='pw', roles=[User.Role.TEACHER])
        cls.outsider = User.objects.create_user(
            username='other', password='pw', roles=[User.Role.TEACHER])
        cls.student = User.objects.create_user(
            username='stud', password='pw', roles=[User.Role.STUDENT])

        cls.course = Course.objects.create(name='Майстер дистиляції')
        cls.subject = make_subject('Сенсорика', course=cls.course)
        cls.group = Group.objects.create(
            name='МД-1', course=cls.course, start_date=MONTH_AGO)
        cls.lesson = GroupSubject.objects.create(
            group=cls.group, subject=cls.subject,
            teacher=cls.teacher, start_date=MONTH_AGO)
        Enrollment.objects.create(
            group=cls.group, student=cls.student, start_date=MONTH_AGO)

        cls.foreign_group = Group.objects.create(
            name='ЗД-1', course=cls.course, start_date=MONTH_AGO)
        GroupSubject.objects.create(
            group=cls.foreign_group, subject=make_subject('Солод', course=cls.course),
            teacher=cls.outsider, start_date=MONTH_AGO)

    def entry(self, **kwargs):
        defaults = dict(
            group=self.group, date=TODAY,
            start_time=dt.time(10), end_time=dt.time(12),
            source=ScheduleEntry.Source.ACADEMY,
            status=ScheduleEntry.Status.ACCEPTED,
            created_by=self.manager,
        )
        return ScheduleEntry.objects.create(**{**defaults, **kwargs})

    # --- кольори -------------------------------------------------------

    def test_colour_follows_who_booked_it_and_how_specific_it_is(self):
        day_for_course = self.entry()
        subject_slot = self.entry(group_subject=self.lesson, start_time=dt.time(12),
                                  end_time=dt.time(14))
        proposal = self.entry(
            group_subject=self.lesson, start_time=dt.time(14), end_time=dt.time(16),
            source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=self.teacher)
        turned_down = self.entry(
            group_subject=self.lesson, start_time=dt.time(16), end_time=dt.time(18),
            source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.REJECTED, created_by=self.teacher)

        self.assertEqual(day_for_course.color, 'sky')
        self.assertEqual(subject_slot.color, 'blue')
        self.assertEqual(proposal.color, 'green')
        self.assertEqual(turned_down.color, 'rejected')

    def test_course_subject_and_teacher_are_read_from_the_group(self):
        slot = self.entry(group_subject=self.lesson)
        self.assertEqual(slot.course, self.course)
        self.assertEqual(slot.subject, self.subject)
        self.assertEqual(slot.teacher, self.teacher)      # з GroupSubject, не з поля
        self.assertEqual(slot.title, 'Сенсорика')

        day = self.entry(start_time=dt.time(12), end_time=dt.time(14))
        self.assertIsNone(day.subject)
        self.assertIsNone(day.teacher)
        self.assertEqual(day.title, 'Майстер дистиляції')

    # --- пропозиція ----------------------------------------------------

    def test_a_teacher_booking_becomes_a_proposal_awaiting_review(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('schedule:add'), {
            'group': self.group.pk, 'date': TODAY.isoformat(),
            'group_subject': self.lesson.pk,
            'start_hour': '10', 'end_hour': '12', 'notes': '',
        })
        proposal = ScheduleEntry.objects.get()
        self.assertEqual(proposal.source, ScheduleEntry.Source.TEACHER)
        self.assertEqual(proposal.status, ScheduleEntry.Status.PROPOSED)
        self.assertEqual(proposal.color, 'green')
        self.assertEqual(proposal.created_by, self.teacher)

    def test_management_booking_is_accepted_straight_away(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('schedule:add'), {
            'group': self.group.pk, 'date': TODAY.isoformat(),
            'group_subject': '', 'start_hour': '10', 'end_hour': '12', 'notes': '',
        })
        booking = ScheduleEntry.objects.get()
        self.assertEqual(booking.source, ScheduleEntry.Source.ACADEMY)
        self.assertEqual(booking.status, ScheduleEntry.Status.ACCEPTED)
        self.assertEqual(booking.color, 'sky')

    def test_accepting_a_proposal_turns_it_into_part_of_the_schedule(self):
        proposal = self.entry(
            group_subject=self.lesson, source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=self.teacher)
        self.client.force_login(self.manager)
        self.client.post(reverse('schedule:accept', args=[proposal.pk]), {})

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ScheduleEntry.Status.ACCEPTED)
        self.assertEqual(proposal.color, 'blue')
        self.assertEqual(proposal.reviewed_by, self.manager)
        self.assertIsNotNone(proposal.reviewed_at)
        # хто запропонував — лишається в історії
        self.assertEqual(proposal.source, ScheduleEntry.Source.TEACHER)
        self.assertEqual(proposal.created_by, self.teacher)

    def test_a_proposal_is_reviewed_once_and_only_by_management(self):
        proposal = self.entry(
            group_subject=self.lesson, source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=self.teacher)
        self.assertTrue(can_review(proposal, self.manager))
        self.assertFalse(can_review(proposal, self.teacher))

        self.client.force_login(self.manager)
        self.client.post(reverse('schedule:reject', args=[proposal.pk]), {})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ScheduleEntry.Status.REJECTED)
        self.assertFalse(can_review(proposal, self.manager))

        # повторний розгляд не перезаписує рішення
        self.client.post(reverse('schedule:accept', args=[proposal.pk]), {})
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ScheduleEntry.Status.REJECTED)

    def test_a_teacher_edits_their_proposal_only_while_it_is_pending(self):
        proposal = self.entry(
            group_subject=self.lesson, source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=self.teacher)
        self.assertTrue(can_modify(proposal, self.teacher))

        proposal.status = ScheduleEntry.Status.ACCEPTED
        self.assertFalse(can_modify(proposal, self.teacher))

    def test_a_teacher_cannot_book_into_a_group_they_do_not_teach_in(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('schedule:add'), {
            'group': self.foreign_group.pk, 'date': TODAY.isoformat(),
            'group_subject': '', 'start_hour': '10', 'end_hour': '12', 'notes': '',
        })
        self.assertEqual(ScheduleEntry.objects.count(), 0)

    # --- вісь календаря ------------------------------------------------

    def test_the_calendar_is_scoped_to_the_groups_you_belong_to(self):
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('schedule:home'))
        self.assertEqual({g.name for g in page.context['groups']}, {'МД-1'})

        self.client.force_login(self.manager)
        page = self.client.get(reverse('schedule:home'))
        self.assertEqual({g.name for g in page.context['groups']}, {'МД-1', 'ЗД-1'})

        # студент бачить розклад своєї групи, але додавати не може
        self.client.force_login(self.student)
        page = self.client.get(reverse('schedule:home'))
        self.assertEqual({g.name for g in page.context['groups']}, {'МД-1'})
        self.assertFalse(page.context['can_add'])


class GroupSubjectManagementTests(TestCase):
    """Наповнення групи предметами — без цього в розкладі нема що обирати."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            username='mgr2', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            username='t1', password='pw', roles=[User.Role.TEACHER])
        cls.other_teacher = User.objects.create_user(
            username='t2', password='pw', roles=[User.Role.TEACHER])

        cls.course = Course.objects.create(name='Майстер дистиляції')
        cls.other_course = Course.objects.create(name='Інший курс')

        cls.solo = make_subject('Сенсорика', course=cls.course, position=1)
        cls.solo.teachers.add(cls.teacher)
        cls.also_solo = make_subject('Вода', course=cls.course, position=2)
        cls.also_solo.teachers.add(cls.other_teacher)
        cls.shared = make_subject('Обладнання', course=cls.course, position=3)
        cls.shared.teachers.add(cls.teacher, cls.other_teacher)
        cls.orphan = make_subject('Випускна робота', course=cls.course, position=4)
        cls.foreign = make_subject('Чуже', course=cls.other_course)

        cls.group = Group.objects.create(
            name='МД-1', course=cls.course, start_date=MONTH_AGO)

    def setUp(self):
        self.client.force_login(self.manager)

    def test_the_form_offers_only_this_courses_subjects(self):
        page = self.client.get(reverse('schedule:group_detail', args=[self.group.pk]))
        offered = set(page.context['subject_form'].fields['subject'].queryset)
        self.assertEqual(offered, {self.solo, self.also_solo, self.shared, self.orphan})
        self.assertNotIn(self.foreign, offered)

    def test_a_manager_adds_a_subject_with_its_teacher_and_dates(self):
        self.client.post(reverse('schedule:group_subject_add', args=[self.group.pk]), {
            'subject': self.solo.pk, 'teacher': self.teacher.pk,
            'start_date': MONTH_AGO.isoformat(), 'end_date': '',
        })
        link = GroupSubject.objects.get()
        self.assertEqual(link.group, self.group)
        self.assertEqual(link.subject, self.solo)
        self.assertEqual(link.teacher, self.teacher)
        self.assertEqual(link.start_date, MONTH_AGO)

    def test_a_subject_already_in_the_group_is_no_longer_offered(self):
        GroupSubject.objects.create(
            group=self.group, subject=self.solo,
            teacher=self.teacher, start_date=MONTH_AGO)
        page = self.client.get(reverse('schedule:group_detail', args=[self.group.pk]))
        self.assertNotIn(self.solo, page.context['subject_form'].fields['subject'].queryset)

    def test_bulk_fill_takes_the_unambiguous_ones_and_reports_the_rest(self):
        response = self.client.post(
            reverse('schedule:group_subjects_fill', args=[self.group.pk]), {}, follow=True)

        added = {link.subject for link in self.group.group_subjects.all()}
        self.assertEqual(added, {self.solo, self.also_solo})   # рівно один викладач
        self.assertEqual(
            self.group.group_subjects.get(subject=self.also_solo).teacher,
            self.other_teacher)

        warning = ' '.join(str(m) for m in response.context['messages'])
        self.assertIn('Обладнання', warning)          # двоє викладачів
        self.assertIn('Випускна робота', warning)     # жодного

    def test_bulk_fill_is_safe_to_repeat(self):
        url = reverse('schedule:group_subjects_fill', args=[self.group.pk])
        self.client.post(url, {})
        before = self.group.group_subjects.count()
        self.client.post(url, {})
        self.assertEqual(self.group.group_subjects.count(), before)

    def test_removing_a_subject_from_the_group(self):
        link = GroupSubject.objects.create(
            group=self.group, subject=self.solo,
            teacher=self.teacher, start_date=MONTH_AGO)
        self.client.post(reverse('schedule:group_subject_delete', args=[link.pk]), {})
        self.assertFalse(GroupSubject.objects.exists())

    def test_a_teacher_cannot_change_the_composition_of_a_group(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('schedule:group_subject_add', args=[self.group.pk]), {
            'subject': self.solo.pk, 'teacher': self.teacher.pk,
            'start_date': MONTH_AGO.isoformat(), 'end_date': '',
        })
        self.assertFalse(GroupSubject.objects.exists())

    def test_filling_the_group_is_what_makes_the_schedule_dropdown_work(self):
        """Саме те, на що натрапила користувачка: порожня група — порожній вибір."""
        empty = self.client.get(reverse('schedule:home'))
        self.assertEqual(len(empty.context['form'].fields['group_subject'].queryset), 0)

        self.client.post(reverse('schedule:group_subjects_fill', args=[self.group.pk]), {})

        filled = self.client.get(reverse('schedule:home'))
        self.assertEqual(
            {link.subject for link in filled.context['form'].fields['group_subject'].queryset},
            {self.solo, self.also_solo},
        )


class ProposalOutcomeTests(TestCase):
    """Доля пропозиції має дійти до викладача, а не чекати, поки він знайде."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            username='mgr3', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            username='t3', password='pw', roles=[User.Role.TEACHER])
        cls.other = User.objects.create_user(
            username='t4', password='pw', roles=[User.Role.TEACHER])

        cls.course = Course.objects.create(name='Курс')
        cls.group = Group.objects.create(
            name='Г-1', course=cls.course, start_date=MONTH_AGO)
        cls.lesson = GroupSubject.objects.create(
            group=cls.group,
            subject=make_subject('Предмет', course=cls.course),
            teacher=cls.teacher, start_date=MONTH_AGO)
        cls.other_lesson = GroupSubject.objects.create(
            group=cls.group,
            subject=make_subject('Інший', course=cls.course),
            teacher=cls.other, start_date=MONTH_AGO)

    def propose(self, author, lesson, hour=10):
        return ScheduleEntry.objects.create(
            group=self.group, group_subject=lesson, date=TODAY,
            start_time=dt.time(hour), end_time=dt.time(hour + 1),
            source=ScheduleEntry.Source.TEACHER,
            status=ScheduleEntry.Status.PROPOSED, created_by=author)

    def review(self, proposal, decision):
        self.client.force_login(self.manager)
        url = 'schedule:accept' if decision == 'accepted' else 'schedule:reject'
        self.client.post(reverse(url, args=[proposal.pk]), {})
        proposal.refresh_from_db()
        return proposal

    def dashboard(self, who):
        self.client.force_login(who)
        return self.client.get(reverse('dashboard:home'))

    def test_a_decision_shows_up_in_the_teachers_dashboard_as_news(self):
        proposal = self.propose(self.teacher, self.lesson)

        waiting = self.dashboard(self.teacher).context
        self.assertEqual(waiting['proposals_pending'], 1)
        self.assertEqual(waiting['proposals_news'], 0)

        self.review(proposal, 'accepted')

        decided = self.dashboard(self.teacher)
        self.assertEqual(decided.context['proposals_pending'], 0)
        self.assertEqual(decided.context['proposals_news'], 1)
        self.assertIn('Є нові рішення: 1', decided.content.decode())

    def test_a_rejection_is_news_just_the_same(self):
        proposal = self.propose(self.teacher, self.lesson)
        self.review(proposal, 'rejected')
        self.assertEqual(self.dashboard(self.teacher).context['proposals_news'], 1)

    def test_the_page_shows_the_decision_and_who_made_it(self):
        proposal = self.review(self.propose(self.teacher, self.lesson), 'rejected')
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('schedule:proposal_list')).content.decode()
        self.assertIn('Відхилено', page)
        self.assertIn(self.manager.username, page)   # немає ПІБ — лишається логін
        self.assertIn('нове', page)                  # підсвічено як новину

    def test_opening_the_page_is_what_counts_as_finding_out(self):
        proposal = self.review(self.propose(self.teacher, self.lesson), 'accepted')
        self.client.force_login(self.teacher)

        first = self.client.get(reverse('schedule:proposal_list'))
        self.assertIn('нове', first.content.decode())   # на цьому ж показі ще видно

        proposal.refresh_from_db()
        self.assertIsNotNone(proposal.author_seen_at)
        self.assertEqual(self.dashboard(self.teacher).context['proposals_news'], 0)
        self.assertNotIn('нове', self.client.get(
            reverse('schedule:proposal_list')).content.decode())

    def test_someone_elses_visit_does_not_count_as_the_authors(self):
        proposal = self.review(self.propose(self.teacher, self.lesson), 'accepted')

        self.client.force_login(self.manager)
        self.client.get(reverse('schedule:proposal_list'))
        proposal.refresh_from_db()
        self.assertIsNone(proposal.author_seen_at)
        self.assertEqual(self.dashboard(self.teacher).context['proposals_news'], 1)

    def test_a_teacher_sees_only_their_own_proposals(self):
        self.propose(self.teacher, self.lesson, hour=10)
        self.propose(self.other, self.other_lesson, hour=12)

        self.client.force_login(self.teacher)
        page = self.client.get(reverse('schedule:proposal_list'))
        self.assertEqual([p.created_by for p in page.context['proposals']], [self.teacher])
        self.assertFalse(page.context['reviewing'])

        self.client.force_login(self.manager)
        page = self.client.get(reverse('schedule:proposal_list'))
        self.assertEqual(len(page.context['proposals']), 2)
        self.assertTrue(page.context['reviewing'])

    def test_management_tile_counts_what_awaits_their_review(self):
        self.propose(self.teacher, self.lesson, hour=10)
        self.propose(self.other, self.other_lesson, hour=12)
        context = self.dashboard(self.manager).context
        self.assertEqual(context['proposals_pending'], 2)
        self.assertEqual(context['proposals_news'], 0)   # своїх пропозицій не має


class CatalogueManagementTests(TestCase):
    """Курси, предмети, групи й студенти правляться на самій платформі."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            username='mgr', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            username='tchr', password='pw', last_name='Бачурін', roles=[User.Role.TEACHER])
        cls.second_teacher = User.objects.create_user(
            username='tchr2', password='pw', last_name='Ражабов', roles=[User.Role.TEACHER])
        cls.master = Course.objects.create(name='Майстер дистиляції')
        cls.grain = Course.objects.create(name='Зернові дистиляти')
        cls.categories = Module.objects.create(course=cls.master, code='2', name='Категорії напоїв')
        cls.grain_programme = Module.objects.create(course=cls.grain, code='1', name='Програма курсу')
        cls.group = Group.objects.create(
            name='МД-1', course=cls.master, start_date=MONTH_AGO,
            end_date=TODAY + dt.timedelta(days=60))

    def setUp(self):
        self.client.force_login(self.manager)

    def subject_payload(self, name, courses=(), teachers=(), existing=0):
        data = {
            'name': name,
            'courses-TOTAL_FORMS': str(len(courses)),
            'courses-INITIAL_FORMS': str(existing),
            'courses-MIN_NUM_FORMS': '0',
            'courses-MAX_NUM_FORMS': '1000',
            # Зайвий порожній список — рядок «+ викладач», у якому нічого не обрали.
            'teachers': [str(t.pk) for t in teachers] + [''],
        }
        for index, row in enumerate(courses):
            for key, value in row.items():
                data[f'courses-{index}-{key}'] = value
        return data

    # --- предмети ------------------------------------------------------

    def test_one_subject_sits_in_several_courses_under_its_own_numbers(self):
        response = self.client.post(reverse('schedule:subject_add'), self.subject_payload(
            'Зернові дистиляти',
            courses=[{'course': self.master.pk, 'code': '2.3', 'module': self.categories.pk},
                     {'course': self.grain.pk, 'code': '1.1', 'module': self.grain_programme.pk}],
            teachers=[self.teacher, self.second_teacher],
        ))
        self.assertRedirects(response, reverse('schedule:subject_list'))
        subject = Subject.objects.get(name='Зернові дистиляти')
        self.assertEqual(
            dict(subject.course_links.values_list('course__name', 'code')),
            {'Майстер дистиляції': '2.3', 'Зернові дистиляти': '1.1'})
        self.assertEqual(set(subject.teachers.all()), {self.teacher, self.second_teacher})

    def test_the_same_course_twice_is_refused(self):
        response = self.client.post(reverse('schedule:subject_add'), self.subject_payload(
            'Ром', courses=[{'course': self.master.pk, 'code': '2.6', 'module': self.categories.pk},
                            {'course': self.master.pk, 'code': '2.7', 'module': self.categories.pk}]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subject.objects.filter(name='Ром').exists())

    def test_a_subject_is_edited_and_removed_from_a_course(self):
        subject = make_subject('Водка', course=self.master, code='2.4')
        CourseSubject.objects.create(course=self.grain, subject=subject, code='3')
        subject.teachers.add(self.teacher)
        links = list(subject.course_links.order_by('course__name'))   # зернові, майстер
        data = self.subject_payload(
            'Горілка',
            courses=[
                {'id': links[0].pk, 'course': self.grain.pk, 'code': '3', 'DELETE': 'on'},
                {'id': links[1].pk, 'course': self.master.pk, 'code': '2.4.1',
                 'module': self.categories.pk},
            ],
            teachers=[self.second_teacher], existing=2)
        response = self.client.post(reverse('schedule:subject_edit', args=[subject.pk]), data)
        self.assertRedirects(response, reverse('schedule:subject_list'))
        subject.refresh_from_db()
        self.assertEqual(subject.name, 'Горілка')
        self.assertEqual(list(subject.course_links.values_list('course__name', 'code')),
                         [('Майстер дистиляції', '2.4.1')])
        self.assertEqual(list(subject.teachers.all()), [self.second_teacher])

    def test_in_a_course_programme_a_subject_always_sits_in_a_module(self):
        response = self.client.post(reverse('schedule:subject_add'), self.subject_payload(
            'Ром', courses=[{'course': self.master.pk, 'code': '2.6'}]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subject.objects.filter(name='Ром').exists())

    def test_a_module_of_another_course_is_refused_by_the_form(self):
        response = self.client.post(reverse('schedule:subject_add'), self.subject_payload(
            'Ром', courses=[{'course': self.master.pk, 'code': '2.6',
                             'module': self.grain_programme.pk}]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subject.objects.filter(name='Ром').exists())

    def test_subjects_are_added_from_the_module_card_not_the_course_card(self):
        course = self.client.get(reverse('schedule:course_detail', args=[self.master.pk]))
        self.assertNotContains(course, reverse('schedule:subject_add'))
        self.assertContains(course, reverse('schedule:module_add'))
        card = self.client.get(reverse('schedule:module_detail', args=[self.categories.pk]))
        add = f'{reverse("schedule:subject_add")}?module={self.categories.pk}'
        self.assertContains(card, add)
        form = self.client.get(add)
        row = form.context['courses'].forms[0]
        self.assertEqual((row.initial['course'], row.initial['module']),
                         (self.master.pk, self.categories.pk))

    def test_a_deleted_module_takes_its_subjects_out_of_the_programme(self):
        subject = make_subject('Ром', course=self.master, code='2.6')
        subject.course_links.update(module=self.categories)
        response = self.client.post(reverse('schedule:module_delete', args=[self.categories.pk]))
        self.assertRedirects(response, reverse('schedule:course_detail', args=[self.master.pk]))
        self.assertFalse(CourseSubject.objects.filter(subject=subject).exists())
        self.assertTrue(Subject.objects.filter(pk=subject.pk).exists(), 'у каталозі лишається')

    def test_teachers_are_picked_from_dropdowns_not_checkboxes(self):
        page = self.client.get(reverse('schedule:subject_add')).content.decode()
        self.assertIn('data-repeat-add', page)
        self.assertNotIn('type="checkbox" name="teachers"', page)

    def test_the_group_shows_the_number_from_its_own_courses_programme(self):
        subject = make_subject('Сенсорика', course=self.master, code='4.1')
        CourseSubject.objects.create(course=self.grain, subject=subject, code='9.9')
        GroupSubject.objects.create(group=self.group, subject=subject, teacher=self.teacher,
                                    start_date=MONTH_AGO)
        page = self.client.get(reverse('schedule:group_detail', args=[self.group.pk]))
        row = page.context['group_subjects'].get()
        self.assertEqual(row.code, '4.1')

    def test_a_subject_taught_in_a_group_cannot_be_deleted_quietly(self):
        subject = make_subject('Сенсорика', course=self.master)
        GroupSubject.objects.create(group=self.group, subject=subject, teacher=self.teacher,
                                    start_date=MONTH_AGO)
        response = self.client.post(reverse('schedule:subject_delete', args=[subject.pk]))
        self.assertRedirects(response, reverse('schedule:subject_list'))
        self.assertTrue(Subject.objects.filter(pk=subject.pk).exists())

    # --- курси ---------------------------------------------------------

    def test_a_course_has_a_card_and_can_be_edited(self):
        make_subject('Сенсорика', course=self.master, code='4.1')
        response = self.client.post(
            reverse('schedule:course_edit', args=[self.master.pk]),
            {'name': 'Майстер дистиляції', 'description': 'Повний курс для виробників.'})
        self.assertRedirects(response, reverse('schedule:course_detail', args=[self.master.pk]))

        self.client.force_login(self.teacher)
        card = self.client.get(reverse('schedule:course_detail', args=[self.master.pk]))
        self.assertContains(card, 'Повний курс для виробників.')
        self.assertContains(card, 'Сенсорика')
        self.assertNotContains(card, reverse('schedule:course_edit', args=[self.master.pk]))
        self.assertRedirects(
            self.client.get(reverse('schedule:course_edit', args=[self.master.pk])),
            reverse('dashboard:home'))

    def test_a_course_with_groups_is_not_deleted_and_its_subjects_survive_deletion(self):
        response = self.client.post(reverse('schedule:course_delete', args=[self.master.pk]))
        self.assertRedirects(response, reverse('schedule:course_detail', args=[self.master.pk]))
        self.assertTrue(Course.objects.filter(pk=self.master.pk).exists())

        subject = make_subject('Солод', course=self.grain)
        self.client.post(reverse('schedule:course_delete', args=[self.grain.pk]))
        self.assertFalse(Course.objects.filter(pk=self.grain.pk).exists())
        self.assertTrue(Subject.objects.filter(pk=subject.pk).exists())

    # --- групи ---------------------------------------------------------

    def test_management_creates_edits_and_deletes_a_group(self):
        response = self.client.post(reverse('schedule:group_add'), {
            'name': 'ЗД-1', 'course': self.grain.pk,
            'start_date': TODAY.isoformat(), 'end_date': '', 'notes': '',
        })
        group = Group.objects.get(name='ЗД-1')
        self.assertRedirects(response, reverse('schedule:group_detail', args=[group.pk]))

        self.client.post(reverse('schedule:group_edit', args=[group.pk]), {
            'name': 'ЗД-2', 'course': self.grain.pk,
            'start_date': TODAY.isoformat(), 'end_date': (TODAY - dt.timedelta(days=1)).isoformat(),
        })
        self.assertFalse(Group.objects.filter(name='ЗД-2').exists(),
                         'завершення раніше за початок не приймається')

        self.client.post(reverse('schedule:group_delete', args=[group.pk]))
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_a_teacher_cannot_touch_groups(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('schedule:group_delete', args=[self.group.pk]))
        self.assertTrue(Group.objects.filter(pk=self.group.pk).exists())
        self.assertRedirects(self.client.get(reverse('schedule:group_add')), reverse('dashboard:home'))

    def test_the_edit_form_shows_dates_the_date_picker_can_read(self):
        page = self.client.get(reverse('schedule:group_edit', args=[self.group.pk]))
        self.assertContains(page, f'value="{MONTH_AGO.isoformat()}"')

    # --- студенти ------------------------------------------------------

    def test_a_new_student_gets_an_account_and_the_groups_dates(self):
        response = self.client.post(reverse('schedule:student_add'), {
            'mode': 'new',
            'new-last_name': 'Коваль', 'new-first_name': 'Олена', 'new-patronymic': '',
            'new-email': '', 'new-username': 'koval',
            'new-password1': 'Very-long-pass-42', 'new-password2': 'Very-long-pass-42',
            'group': self.group.pk, 'start_date': '', 'end_date': '',
        })
        self.assertRedirects(response, reverse('schedule:student_list'))
        student = User.objects.get(username='koval')
        self.assertEqual(student.roles, {User.Role.STUDENT})
        enrollment = student.enrollments.get()
        self.assertEqual((enrollment.group, enrollment.start_date, enrollment.end_date),
                         (self.group, self.group.start_date, self.group.end_date))

    def test_someone_already_on_the_platform_is_enrolled_without_a_second_account(self):
        existing = User.objects.create_user(username='old', roles=[User.Role.STUDENT])
        self.client.post(reverse('schedule:student_add'), {
            'mode': 'existing', 'student': existing.pk, 'group': self.group.pk,
            'start_date': TODAY.isoformat(), 'end_date': '',
            # поля нового студента порожні — у цьому режимі їх не перевіряють
            'new-username': '',
        })
        self.assertEqual(User.objects.filter(username='old').count(), 1)
        self.assertEqual(existing.enrollments.get().start_date, TODAY)

    def test_a_students_enrollment_and_name_are_edited_and_the_row_removed(self):
        student = User.objects.create_user(
            username='stud', last_name='Стара', roles=[User.Role.STUDENT])
        enrollment = Enrollment.objects.create(group=self.group, student=student, start_date=MONTH_AGO)
        response = self.client.post(reverse('schedule:student_edit', args=[enrollment.pk]), {
            'group': self.group.pk, 'start_date': MONTH_AGO.isoformat(), 'end_date': TODAY.isoformat(),
            'info-last_name': 'Нова', 'info-first_name': 'Ірина', 'info-patronymic': '', 'info-email': '',
        })
        self.assertRedirects(response, reverse('schedule:student_list'))
        enrollment.refresh_from_db()
        student.refresh_from_db()
        self.assertEqual(enrollment.end_date, TODAY)
        self.assertEqual(student.last_name, 'Нова')

        back = reverse('schedule:group_detail', args=[self.group.pk])
        response = self.client.post(
            reverse('schedule:student_delete', args=[enrollment.pk]), {'next': back})
        self.assertRedirects(response, back)
        self.assertFalse(Enrollment.objects.filter(pk=enrollment.pk).exists())
        self.assertTrue(User.objects.filter(pk=student.pk).exists(), 'обліковий запис лишається')

    def test_a_foreign_next_is_ignored(self):
        student = User.objects.create_user(username='stud', roles=[User.Role.STUDENT])
        enrollment = Enrollment.objects.create(group=self.group, student=student, start_date=MONTH_AGO)
        response = self.client.post(
            reverse('schedule:student_delete', args=[enrollment.pk]), {'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('schedule:student_list'))

    def test_a_teacher_cannot_manage_students(self):
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get(reverse('schedule:student_add')), reverse('dashboard:home'))
        student = User.objects.create_user(username='stud', roles=[User.Role.STUDENT])
        enrollment = Enrollment.objects.create(group=self.group, student=student, start_date=MONTH_AGO)
        self.client.post(reverse('schedule:student_delete', args=[enrollment.pk]))
        self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk).exists())

    def test_period_columns_carry_their_bounds_for_the_filter(self):
        page = self.client.get(reverse('schedule:group_list')).content.decode()
        self.assertIn('data-filter="period"', page)
        self.assertIn(f'data-start="{MONTH_AGO.isoformat()}" data-end="{self.group.end_date.isoformat()}"', page)


from decimal import Decimal

from django.core.exceptions import ValidationError

from . import pricing


class ImportedPricingTests(TestCase):
    """«Майстер» після імпорту: модулі, години, ставки — і вартість курсу."""

    def test_the_master_course_adds_up_to_what_the_academy_agreed(self):
        call_command('import_program', verbosity=0)
        course = Course.objects.get(name=programs.COURSE)
        self.assertEqual(course.modules.count(), 11)
        self.assertEqual(course.ordered_program.first().subject.name,
                         'Вступне слово: як проходить курс, випускна робота')
        self.assertEqual(course.group_price_eur, 1200)
        self.assertEqual(course.excursion_price, 5000)
        self.assertEqual(User.objects.get(username='ivan-bachurin').hourly_rate, 2000)
        _, total = pricing.program_cost(course.ordered_program)
        self.assertEqual(total.hours, Decimal('145'))
        self.assertEqual(total.teachers, 161_000)        # 129 год × 1000 + 16 год Бачуріна × 2000
        self.assertEqual(total.academy, 48_300)          # 30%
        self.assertEqual(total.price, 209_300)

    def test_reimport_keeps_what_managers_changed(self):
        call_command('import_program', verbosity=0)
        link = CourseSubject.objects.get(subject__name='Водка')
        link.hours = Decimal('6')
        link.save()
        bachurin = User.objects.get(username='ivan-bachurin')
        bachurin.hourly_rate = 2500
        bachurin.save()
        call_command('import_program', verbosity=0)
        link.refresh_from_db()
        bachurin.refresh_from_db()
        self.assertEqual(link.hours, Decimal('6'))
        self.assertEqual(bachurin.hourly_rate, 2500)


class PricingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name='Курс')
        cls.teacher = User.objects.create_user(username='t', roles=[User.Role.TEACHER])
        cls.star = User.objects.create_user(username='s', hourly_rate=2000,
                                            roles=[User.Role.TEACHER])

    def link(self, hours, *teachers):
        subject = make_subject(f'Предмет {hours}', course=self.course)
        subject.teachers.set(teachers)
        link = subject.course_links.get()
        link.hours = hours
        return link

    def test_hour_costs_the_teacher_rate_plus_commission(self):
        cost = pricing.link_cost(self.link(Decimal('3'), self.teacher))
        self.assertEqual((cost.teachers, cost.academy, cost.price), (3000, 900, 3900))

    def test_with_several_teachers_the_highest_rate_counts(self):
        cost = pricing.link_cost(self.link(Decimal('2'), self.teacher, self.star))
        self.assertEqual(cost.rate, 2000)

    def test_a_subject_without_teachers_costs_the_standard_rate(self):
        self.assertEqual(pricing.link_cost(self.link(Decimal('1.5'))).teachers, 1500)

    def test_a_subject_without_hours_is_left_out_of_the_total(self):
        rows, total = pricing.program_cost([self.link(None, self.teacher),
                                            self.link(Decimal('1'), self.teacher)])
        self.assertIsNone(rows[0][1])
        self.assertEqual(total.teachers, 1000)


class CostVisibilityTests(TestCase):
    """Суми бачать менеджер і супер-адмін; решта — програму з годинами без грошей."""

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name='Майстер дистиляції', excursion_price=5000)
        cls.module = Module.objects.create(course=cls.course, code='2', name='Категорії напоїв')
        cls.teacher = User.objects.create_user(
            username='bachurin', last_name='Бачурін', hourly_rate=2000, roles=[User.Role.TEACHER])
        cls.subject = make_subject('Водка', course=cls.course, code='2.4')
        cls.subject.teachers.add(cls.teacher)
        cls.subject.course_links.update(module=cls.module, hours=Decimal('4'))
        cls.people = {
            role: User.objects.create_user(username=role, roles=[role])
            for role in (User.Role.SUPER_ADMIN, User.Role.MANAGER, User.Role.TEACHER,
                         User.Role.STUDENT)
        }

    def pages(self):
        return [reverse('schedule:course_detail', args=[self.course.pk]),
                reverse('schedule:module_detail', args=[self.module.pk]),
                reverse('schedule:subject_detail', args=[self.subject.pk])]

    def test_managers_see_the_money(self):
        for role in (User.Role.SUPER_ADMIN, User.Role.MANAGER):
            self.client.force_login(self.people[role])
            for url in self.pages():
                with self.subTest(role=role, url=url):
                    self.assertContains(self.client.get(url), '10 400')   # 4 год × 2000 + 30%

    def test_everyone_else_sees_hours_but_no_money(self):
        for role in (User.Role.TEACHER, User.Role.STUDENT):
            self.client.force_login(self.people[role])
            for url in self.pages():
                with self.subTest(role=role, url=url):
                    page = self.client.get(url)
                    self.assertEqual(page.status_code, 200)
                    self.assertContains(page, 'Водка')
                    self.assertContains(page, 'Годин')
                    for secret in ('₴', '2 000', '10 400', 'Викладачам',
                                   'Академії 30%', '5 000'):
                        self.assertNotContains(page, secret)

    def test_the_rate_is_set_by_a_manager_on_the_user_form(self):
        self.client.force_login(self.people[User.Role.MANAGER])
        form = self.client.get(reverse('accounts:user_edit', args=[self.teacher.pk]))
        self.assertContains(form, 'name="hourly_rate"')
        self.client.force_login(self.teacher)
        self.assertNotContains(self.client.get(reverse('accounts:account')), 'hourly_rate')

    def test_a_module_of_another_course_is_refused(self):
        foreign = Module.objects.create(course=Course.objects.create(name='Інший'), name='Чужий')
        link = self.subject.course_links.get()
        link.module = foreign
        with self.assertRaises(ValidationError):
            link.full_clean()


from unittest import mock
from urllib.error import URLError

from django.core.cache import cache
from django.utils import timezone

from . import exchange
from .models import EuroRate


class EuroRateTests(TestCase):
    """Курс НБУ: питаємо раз на день, без НБУ — останній відомий."""

    def setUp(self):
        # Позначка «НБУ не відповів» живе в кеші й пережила б інші тести.
        cache.clear()

    def test_a_failed_nbu_is_not_asked_again_for_an_hour(self):
        with mock.patch.object(exchange, 'fetch', side_effect=URLError('down')) as fetch:
            exchange.today_rate()
            exchange.today_rate()
        fetch.assert_called_once()

    def test_the_rate_is_asked_once_a_day(self):
        with mock.patch.object(exchange, 'fetch', return_value=Decimal('50.4977')) as fetch:
            self.assertEqual(exchange.today_rate().rate, Decimal('50.4977'))
            exchange.today_rate()
        fetch.assert_called_once()

    def test_without_the_nbu_the_last_known_rate_is_used(self):
        EuroRate.objects.create(date=TODAY - dt.timedelta(days=2), rate=Decimal('49.9'))
        with mock.patch.object(exchange, 'fetch', side_effect=URLError('down')):
            self.assertEqual(exchange.today_rate().rate, Decimal('49.9'))

    def test_without_any_rate_there_is_none(self):
        with mock.patch.object(exchange, 'fetch', side_effect=URLError('down')):
            self.assertIsNone(exchange.today_rate())


class CourseOffersTests(TestCase):
    """Чотири ціни курсу: Академії, група, Early Bird, індивідуально."""

    def test_offers_are_in_hryvnias_with_euros(self):
        course = Course(group_price_eur=1200, excursion_price=5000)
        total = pricing.Cost(Decimal('145'), 161_000, 48_300)
        offers = pricing.course_offers(course, total, Decimal('50'))
        self.assertEqual(offers['academy'], pricing.Money(161_000, 3220))
        self.assertEqual(offers['group'], pricing.Money(60_000, 1200))
        self.assertEqual(offers['early_bird'], pricing.Money(55_000, 1100))   # мінус екскурсія
        self.assertEqual(offers['individual'], pricing.Money(209_300, 4186))

    def test_without_a_group_price_there_are_no_group_offers(self):
        offers = pricing.course_offers(Course(), pricing.Cost(Decimal('1'), 1000, 300), None)
        self.assertIsNone(offers['group'])
        self.assertIsNone(offers['early_bird'])
        self.assertEqual(offers['individual'], pricing.Money(1300, None))


class CoursePricesPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(name='Майстер дистиляції', group_price_eur=1200,
                                           excursion_price=5000)
        module = Module.objects.create(course=cls.course, code='1', name='Вступ')
        subject = make_subject('Техніка безпеки', course=cls.course, code='1.1')
        subject.course_links.update(module=module, hours=Decimal('3'))
        EuroRate.objects.create(date=timezone.localdate(), rate=Decimal('50'))
        cls.manager = User.objects.create_user(username='mgr', roles=[User.Role.MANAGER])
        cls.student = User.objects.create_user(username='st', roles=[User.Role.STUDENT])

    def test_the_manager_sees_four_prices_and_todays_rate(self):
        self.client.force_login(self.manager)
        page = self.client.get(reverse('schedule:course_detail', args=[self.course.pk]))
        for text in ('Для Академії', 'Студент загальної групи', 'Early Bird',
                     'Індивідуальний студент', '1&nbsp;€ = 50,00&nbsp;₴',
                     '60 000', '55 000', '3 900'):
            self.assertContains(page, text)

    def test_modules_fold_for_everyone(self):
        self.client.force_login(self.student)
        page = self.client.get(reverse('schedule:course_detail', args=[self.course.pk]))
        self.assertContains(page, '<details class="module-block" open>')
        self.assertContains(page, 'data-modules-toggle')
        self.assertNotContains(page, 'Early Bird')
