import datetime as dt

from django.conf import settings
from django.db import models


class TaskQuerySet(models.QuerySet):
    def for_user(self, user):
        """Свої задачі людини плюс спільні задачі керування, якщо вона керує."""
        visible = models.Q(assignee=user)
        if user.can_manage_users:
            visible |= models.Q(assignee__isnull=True)
        return self.filter(visible)

    def open(self):
        return self.filter(done_at__isnull=True)

    def done(self):
        return self.filter(done_at__isnull=False)

    def reminding(self, on=None):
        """Відкриті задачі, про які вже час нагадувати."""
        return self.open().filter(remind_on__lte=on or dt.date.today())

    def overdue(self, on=None):
        return self.open().filter(due_date__lt=on or dt.date.today())


class Task(models.Model):
    """Задача або нагадування в особистому календарі «Мої задачі».

    Задача без виконавця — спільна для керування: її бачать усі менеджери й
    супер-адміни, і виконана одним, вона закривається для всіх. Так живуть
    нагадування про виплати викладачам — платить хтось один.

    Задачі, які ставить сама платформа, мають `key` («payday:2026-10-15»):
    за ним вона не створює ту саму задачу вдруге, а людина не може її
    видалити — лише виконати.

    `remind_on` — з якого дня задача «горить» у кабінеті. Коли запрацює
    пошта, з цього ж дня полетить лист.
    """

    title = models.CharField('Задача', max_length=200)
    notes = models.TextField('Примітка', blank=True)
    due_date = models.DateField('Термін')
    remind_on = models.DateField(
        'Нагадати з', blank=True,
        help_text='Порожньо — у день терміну.',
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name='tasks', verbose_name='Чия задача',
        help_text='Порожньо — спільна задача керування.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_tasks', verbose_name='Поставив(ла)',
        help_text='Порожньо — поставила платформа.',
    )
    key = models.CharField('Ключ платформи', max_length=100, unique=True, null=True,
                           blank=True, editable=False)
    link = models.CharField('Посилання', max_length=300, blank=True)
    done_at = models.DateTimeField('Виконано', null=True, blank=True)
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='done_tasks', verbose_name='Виконав(ла)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ['due_date', 'pk']
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачі'

    def __str__(self):
        return f'{self.due_date:%d.%m.%Y} — {self.title}'

    def save(self, *args, **kwargs):
        if self.remind_on is None:
            self.remind_on = self.due_date
        super().save(*args, **kwargs)

    @property
    def is_done(self):
        return self.done_at is not None

    @property
    def is_shared(self):
        return self.assignee_id is None

    @property
    def is_system(self):
        return self.key is not None

    @property
    def is_overdue(self):
        return not self.is_done and self.due_date < dt.date.today()

    def can_delete(self, user):
        """Видалити можна лише задачу, яку людина поставила собі сама."""
        return not self.is_system and self.created_by_id == user.pk
