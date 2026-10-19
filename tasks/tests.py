import datetime as dt

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Task

TODAY = dt.date.today()


class TaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(username, *roles):
            return User.objects.create_user(username=username, password='pw', roles=roles)

        cls.admin = user('admin', User.Role.SUPER_ADMIN)
        cls.manager = user('manager', User.Role.MANAGER)
        cls.teacher = user('teacher', User.Role.TEACHER)
        cls.shared = Task.objects.create(
            title='Виплата викладачам', due_date=TODAY, key='payday:test')
        cls.own = Task.objects.create(
            title='Подзвонити на дистилерію', due_date=TODAY + dt.timedelta(days=5),
            assignee=cls.teacher, created_by=cls.teacher)

    def visible(self, who):
        return set(Task.objects.for_user(who))

    def test_shared_tasks_belong_to_every_manager_and_nobody_else(self):
        self.assertEqual(self.visible(self.manager), {self.shared})
        self.assertEqual(self.visible(self.admin), {self.shared})
        self.assertEqual(self.visible(self.teacher), {self.own})

    def test_reminder_date_defaults_to_the_due_date(self):
        self.assertEqual(self.own.remind_on, self.own.due_date)
        self.assertEqual(list(Task.objects.for_user(self.teacher).reminding()), [])
        self.assertEqual(
            list(Task.objects.for_user(self.teacher).reminding(on=self.own.due_date)), [self.own])

    def test_done_by_one_manager_is_done_for_all(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('tasks:done', args=[self.shared.pk]), {'done': '1'})
        self.shared.refresh_from_db()
        self.assertTrue(self.shared.is_done)
        self.assertEqual(self.shared.done_by, self.manager)
        self.assertFalse(Task.objects.for_user(self.admin).open().exists())
        # і повернути можна
        self.client.post(reverse('tasks:done', args=[self.shared.pk]), {'done': '0'})
        self.shared.refresh_from_db()
        self.assertFalse(self.shared.is_done)

    def test_nobody_touches_someone_elses_task(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('tasks:done', args=[self.own.pk]), {'done': '1'})
        self.client.post(reverse('tasks:delete', args=[self.own.pk]))
        self.own.refresh_from_db()
        self.assertFalse(self.own.is_done)

    def test_platform_reminders_can_be_done_but_not_deleted(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('tasks:delete', args=[self.shared.pk]))
        self.assertTrue(Task.objects.filter(pk=self.shared.pk).exists())

    def test_own_task_can_be_deleted(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('tasks:delete', args=[self.own.pk]))
        self.assertFalse(Task.objects.filter(pk=self.own.pk).exists())

    def test_a_teacher_adds_a_task_for_themself_only(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('tasks:add'), {
            'title': 'Підготувати дегустацію', 'due_date': TODAY.isoformat(), 'shared': 'on'})
        task = Task.objects.get(title='Підготувати дегустацію')
        self.assertEqual(task.assignee, self.teacher)
        self.assertEqual(task.created_by, self.teacher)

    def test_a_manager_can_share_a_task_with_management(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('tasks:add'), {
            'title': 'Звірити ставки', 'due_date': TODAY.isoformat(), 'shared': 'on'})
        task = Task.objects.get(title='Звірити ставки')
        self.assertIsNone(task.assignee)
        self.assertIn(task, self.visible(self.admin))

    def test_reminder_after_the_due_date_is_refused(self):
        self.client.force_login(self.teacher)
        page = self.client.post(reverse('tasks:add'), {
            'title': 'Пізно', 'due_date': TODAY.isoformat(),
            'remind_on': (TODAY + dt.timedelta(days=1)).isoformat()})
        self.assertContains(page, 'Нагадування не може бути пізніше за термін.')
        self.assertFalse(Task.objects.filter(title='Пізно').exists())

    def test_my_tasks_page_shows_the_calendar_and_the_list(self):
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('tasks:list'))
        self.assertContains(page, 'Подзвонити на дистилерію')
        self.assertNotContains(page, 'Виплата викладачам')

    def test_dashboard_counts_what_is_due_now(self):
        self.client.force_login(self.manager)
        page = self.client.get(reverse('dashboard:home'))
        self.assertEqual(page.context['tasks_due'], 1)
        self.assertContains(page, '<h3>Мої задачі</h3>', html=False)
        self.assertContains(page, '<h3>Виплати викладачам</h3>', html=False)

    def test_teachers_have_no_accounting_on_the_dashboard(self):
        self.client.force_login(self.teacher)
        page = self.client.get(reverse('dashboard:home'))
        self.assertContains(page, '<h3>Мої задачі</h3>', html=False)
        self.assertNotContains(page, 'Виплати викладачам')
        self.assertNotContains(page, 'Бухгалтерія')
