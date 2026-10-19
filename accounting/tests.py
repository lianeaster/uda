import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schedule.models import Course, Group, GroupSubject, ScheduleEntry
from schedule.templatetags.pricing import uah
from schedule.testing import make_subject
from tasks.models import Task

from . import payroll

D = dt.date


class PaydayTests(TestCase):
    """15-го платять за 1–15, 30-го — за 16-те до кінця місяця."""

    def test_lessons_up_to_the_15th_are_paid_on_the_15th(self):
        for day in (1, 9, 15):
            with self.subTest(day=day):
                self.assertEqual(payroll.payday_for(D(2026, 10, day)), D(2026, 10, 15))

    def test_lessons_after_the_15th_are_paid_on_the_30th_even_the_31st(self):
        for day in (16, 30, 31):
            with self.subTest(day=day):
                self.assertEqual(payroll.payday_for(D(2026, 10, day)), D(2026, 10, 30))

    def test_february_pays_on_its_last_day(self):
        self.assertEqual(payroll.payday_for(D(2026, 2, 20)), D(2026, 2, 28))
        self.assertEqual(payroll.payday_for(D(2028, 2, 29)), D(2028, 2, 29))
        self.assertEqual(payroll.period(D(2026, 2, 28)), (D(2026, 2, 16), D(2026, 2, 28)))

    def test_second_period_runs_to_the_end_of_the_month(self):
        self.assertEqual(payroll.period(D(2026, 10, 30)), (D(2026, 10, 16), D(2026, 10, 31)))
        self.assertEqual(payroll.period(D(2026, 10, 15)), (D(2026, 10, 1), D(2026, 10, 15)))

    def test_next_payday_after_the_31st_is_the_15th_of_next_month(self):
        self.assertEqual(payroll.next_payday(D(2026, 10, 31)), D(2026, 11, 15))
        self.assertEqual(payroll.next_payday(D(2026, 12, 31)), D(2027, 1, 15))
        self.assertEqual(payroll.next_payday(D(2026, 10, 15)), D(2026, 10, 15))
        self.assertEqual(payroll.next_payday(D(2026, 10, 19)), D(2026, 10, 30))

    def test_paydays_step_through_the_year(self):
        self.assertEqual(payroll.previous_payday(D(2026, 3, 15)), D(2026, 2, 28))
        self.assertEqual(payroll.following_payday(D(2026, 2, 28)), D(2026, 3, 15))
        self.assertEqual(payroll.following_payday(D(2026, 12, 30)), D(2027, 1, 15))
        self.assertEqual(payroll.previous_payday(D(2027, 1, 15)), D(2026, 12, 30))


class StatementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user('manager', password='pw', roles=[User.Role.MANAGER])
        cls.teacher = User.objects.create_user(
            'teacher', password='pw', first_name='Марина', last_name='Чехун',
            roles=[User.Role.TEACHER], hourly_rate=1200)
        cls.standard = User.objects.create_user(
            'standard', password='pw', first_name='Іван', last_name='Бачурін',
            roles=[User.Role.TEACHER])
        course = Course.objects.create(name='Майстер дистиляції')
        group = cls.group = Group.objects.create(name='МД-8', course=course, start_date=D(2026, 9, 1))
        cls.sensory = GroupSubject.objects.create(
            group=group, subject=make_subject('Сенсорика', course=course),
            teacher=cls.teacher, start_date=D(2026, 9, 1))
        cls.grain = GroupSubject.objects.create(
            group=group, subject=make_subject('Зерно', course=course),
            teacher=cls.standard, start_date=D(2026, 9, 1))

    def lesson(self, day, start, end, group_subject=None, **extra):
        extra.setdefault('source', ScheduleEntry.Source.ACADEMY)
        return ScheduleEntry.objects.create(
            group=self.group, group_subject=group_subject, date=day,
            start_time=dt.time(*start), end_time=dt.time(*end),
            created_by=self.manager, **extra)

    def test_pays_each_teacher_hours_times_their_rate(self):
        self.lesson(D(2026, 10, 2), (10,), (13,), self.sensory)
        self.lesson(D(2026, 10, 9), (10,), (11, 30), self.sensory)
        self.lesson(D(2026, 10, 10), (14,), (16,), self.grain)
        report = payroll.statement(D(2026, 10, 15))
        pays = {pay.teacher: pay for pay in report.teachers}
        self.assertEqual(pays[self.teacher].hours, Decimal('4.5'))
        self.assertEqual(pays[self.teacher].amount, 5400)        # 4,5 × 1200
        self.assertEqual(pays[self.standard].amount, 2000)       # 2 × стандартна 1000
        self.assertEqual(report.amount, 7400)
        self.assertEqual(report.lesson_count, 3)

    def test_only_lessons_of_the_period_count(self):
        self.lesson(D(2026, 10, 15), (10,), (11,), self.sensory)
        self.lesson(D(2026, 10, 16), (10,), (11,), self.sensory)
        self.assertEqual(payroll.statement(D(2026, 10, 15)).amount, 1200)
        self.assertEqual(payroll.statement(D(2026, 10, 30)).amount, 1200)

    def test_pending_rejected_and_teacherless_slots_are_not_paid(self):
        self.lesson(D(2026, 10, 3), (10,), (12,), self.sensory,
                    source=ScheduleEntry.Source.TEACHER, status=ScheduleEntry.Status.PROPOSED)
        self.lesson(D(2026, 10, 4), (10,), (12,), self.sensory,
                    source=ScheduleEntry.Source.TEACHER, status=ScheduleEntry.Status.REJECTED)
        self.lesson(D(2026, 10, 5), (10,), (12,))   # день під курс, без предмета
        report = payroll.statement(D(2026, 10, 15))
        self.assertEqual(report.amount, 0)
        self.assertEqual(len(report.pending), 1)
        self.assertEqual(len(report.without_teacher), 1)

    def test_accepted_proposal_is_paid_to_the_subjects_teacher(self):
        self.lesson(D(2026, 10, 3), (10,), (12,), self.sensory,
                    source=ScheduleEntry.Source.TEACHER, status=ScheduleEntry.Status.ACCEPTED)
        self.assertEqual(payroll.statement(D(2026, 10, 15)).amount, 2400)

    # --- сторінка -------------------------------------------------------

    def test_only_management_opens_the_payroll(self):
        url = reverse('accounting:payroll')
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get(url), reverse('dashboard:home'))
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_payroll_page_shows_the_requested_payday_and_the_sums(self):
        self.lesson(D(2026, 10, 20), (10,), (13,), self.sensory)
        self.client.force_login(self.manager)
        page = self.client.get(reverse('accounting:payroll'), {'payday': '2026-10-21'})
        self.assertEqual(page.context['report'].payday, D(2026, 10, 30))
        self.assertContains(page, 'Чехун Марина')
        self.assertContains(page, uah(3600))

    # --- нагадування ----------------------------------------------------

    def test_a_lesson_in_the_schedule_puts_one_shared_reminder_on_its_payday(self):
        self.lesson(D(2026, 10, 20), (10,), (13,), self.sensory)
        self.lesson(D(2026, 10, 22), (10,), (13,), self.grain)
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        task = Task.objects.get()
        self.assertEqual(task.key, 'payday:2026-10-30')
        self.assertEqual(task.due_date, D(2026, 10, 30))
        self.assertEqual(task.remind_on, D(2026, 10, 27))
        self.assertIsNone(task.assignee)
        self.assertIn('payday=2026-10-30', task.link)

    def test_no_reminder_for_slots_nobody_is_paid_for(self):
        self.lesson(D(2026, 10, 20), (10,), (12,))
        self.lesson(D(2026, 10, 21), (10,), (12,), self.sensory,
                    source=ScheduleEntry.Source.TEACHER, status=ScheduleEntry.Status.PROPOSED)
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        self.assertFalse(Task.objects.exists())

    def test_the_previous_payday_keeps_its_reminder_older_ones_do_not_appear(self):
        self.lesson(D(2026, 9, 5), (10,), (12,), self.sensory)    # виплата 15.09
        self.lesson(D(2026, 10, 5), (10,), (12,), self.sensory)   # виплата 15.10 — щойно минула
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        self.assertEqual(list(Task.objects.values_list('key', flat=True)), ['payday:2026-10-15'])

    def test_a_done_reminder_stays_done(self):
        self.lesson(D(2026, 10, 20), (10,), (13,), self.sensory)
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        Task.objects.update(done_at=dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc))
        self.lesson(D(2026, 10, 21), (10,), (13,), self.sensory)
        payroll.sync_payday_tasks(on=D(2026, 10, 19))
        self.assertTrue(Task.objects.get().is_done)
