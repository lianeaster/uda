from django.core.management import call_command
from django.test import TestCase

from accounts.models import User

from . import programs
from .models import Course, Subject


class ImportProgramTests(TestCase):
    """Предмети програми курсу та їхні викладачі з графіка 8-ї групи."""

    def import_program(self, **options):
        call_command('import_program', verbosity=0, **options)

    def test_every_numbered_item_becomes_a_subject_of_the_course(self):
        self.import_program()
        course = Course.objects.get(name=programs.COURSE)
        expected = list(programs.subjects())
        self.assertEqual(course.subjects.count(), len(expected))
        for position, code, name, _module, _lecturers in expected:
            with self.subTest(code=code):
                subject = Subject.objects.get(name=name)
                self.assertEqual(subject.course, course)
                self.assertEqual(subject.code, code)
                self.assertEqual(subject.position, position)

    def test_subjects_keep_the_order_of_the_programme_not_the_alphabet(self):
        self.import_program()
        codes = list(
            Subject.objects.filter(course__name=programs.COURSE)
            .values_list('code', flat=True)
        )
        self.assertEqual(codes, [code for _, code, _, _, _ in programs.subjects()])
        # за абеткою «10.1» стояло б перед «2.1» — саме тому є `position`
        self.assertLess(codes.index('2.1'), codes.index('10.1'))

    def test_teachers_are_linked_to_what_the_schedule_says_they_teach(self):
        self.import_program()
        bachurin = User.objects.get(username='ivan-bachurin')
        self.assertEqual(
            sorted(bachurin.subjects.values_list('code', flat=True)),
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
            sorted(bilko.subjects.values_list('code', flat=True)),
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
        before = {
            (s.pk, s.code, s.position, tuple(sorted(s.teachers.values_list('pk', flat=True))))
            for s in Subject.objects.all()
        }
        self.import_program()
        after = {
            (s.pk, s.code, s.position, tuple(sorted(s.teachers.values_list('pk', flat=True))))
            for s in Subject.objects.all()
        }
        self.assertEqual(after, before)

    def test_dry_run_writes_nothing(self):
        self.import_program(dry_run=True)
        self.assertEqual(Subject.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)

    def test_subjects_of_the_course_outside_the_programme_are_left_alone(self):
        course = Course.objects.create(name=programs.COURSE)
        stray = Subject.objects.create(name='Старий предмет', course=course)
        self.import_program()
        stray.refresh_from_db()
        self.assertEqual(stray.course, course)
        self.assertEqual(stray.position, 0)


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
        cls.subject = Subject.objects.create(name='Сенсорика', course=cls.course)
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
            group=cls.foreign_group, subject=Subject.objects.create(
                name='Солод', course=cls.course),
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

        cls.solo = Subject.objects.create(name='Сенсорика', course=cls.course, position=1)
        cls.solo.teachers.add(cls.teacher)
        cls.also_solo = Subject.objects.create(name='Вода', course=cls.course, position=2)
        cls.also_solo.teachers.add(cls.other_teacher)
        cls.shared = Subject.objects.create(name='Обладнання', course=cls.course, position=3)
        cls.shared.teachers.add(cls.teacher, cls.other_teacher)
        cls.orphan = Subject.objects.create(name='Випускна робота', course=cls.course, position=4)
        cls.foreign = Subject.objects.create(name='Чуже', course=cls.other_course)

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
            subject=Subject.objects.create(name='Предмет', course=cls.course),
            teacher=cls.teacher, start_date=MONTH_AGO)
        cls.other_lesson = GroupSubject.objects.create(
            group=cls.group,
            subject=Subject.objects.create(name='Інший', course=cls.course),
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
