from django.conf import settings
from django.db import models


class Course(models.Model):
    """A full program, e.g. «Майстер дистиляції» or «Зернові дистиляти»."""

    name = models.CharField('Назва курсу', max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Курс'
        verbose_name_plural = 'Курси'

    def __str__(self):
        return self.name


class Subject(models.Model):
    """A specific topic within a course, e.g. «Сенсорний аналіз», taught by one or more teachers."""

    name = models.CharField('Назва предмету', max_length=200, unique=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name='Курс',
        null=True,
    )
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='subjects',
        blank=True,
        limit_choices_to={'role': 'teacher'},
        verbose_name='Викладачі',
    )

    class Meta:
        ordering = ['course__name', 'name']
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предмети'

    def __str__(self):
        return f'{self.course.name} — {self.name}'


class ScheduleEntry(models.Model):
    """One lesson slot: either a bare course reservation (blue) or a fully
    specified booking with a subject and a teacher (green). Where a blue and
    a green entry overlap in time, the overlapping range is rendered orange.
    """

    class Source(models.TextChoices):
        ACADEMY = 'academy', 'Академія'
        TEACHER = 'teacher', 'Викладач'

    title = models.CharField('Назва', max_length=200)
    date = models.DateField('Дата')
    start_time = models.TimeField('Початок')
    end_time = models.TimeField('Кінець')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Викладач',
        null=True,
        blank=True,
    )
    source = models.CharField('Джерело', max_length=10, choices=Source.choices)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        related_name='schedule_entries',
        null=True,
        blank=True,
        verbose_name='Курс',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        related_name='schedule_entries',
        null=True,
        blank=True,
        verbose_name='Предмет',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_schedule_entries',
        verbose_name='Створив(ла)',
    )
    notes = models.TextField('Примітка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Запис розкладу'
        verbose_name_plural = 'Записи розкладу'

    def __str__(self):
        return f'{self.date} {self.start_time}-{self.end_time} — {self.title}'

    def overlaps(self, other):
        if self.date != other.date:
            return False
        if not (self.start_time < other.end_time and other.start_time < self.end_time):
            return False
        # A reservation with no teacher yet is an Academy-wide time block, so
        # it can conflict with any teacher's booking at an overlapping time.
        if self.teacher_id is None or other.teacher_id is None:
            return True
        return self.teacher_id == other.teacher_id
