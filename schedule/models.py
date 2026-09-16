import datetime as dt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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
    """A specific topic within a course, e.g. «Сенсорний аналіз», taught by one or more teachers.

    Nothing here (nor in `ScheduleEntry`, `GroupSubject`, `Enrollment`) narrows
    its link to users by role. Roles are a set that grows over time, so a role
    filter baked into the field would both break once `User.role` stopped being
    a column and retroactively invalidate links made under an earlier role.
    Forms pick the right people with `User.objects.with_role(...)`.
    """

    name = models.CharField('Назва предмету', max_length=200, unique=True)
    # Номер із програми курсу («2.1», «10.4»). Лишаємо рядком і як у джерелі:
    # у графіку трапляються повтори (два «8.2», два «10.7»), тож це підпис для
    # людини, а не ключ. Порядок тримає `position`, бо «10.1» < «2.1» за абеткою.
    code = models.CharField('Номер у програмі', max_length=20, blank=True)
    position = models.PositiveIntegerField('Порядок у програмі', default=0)
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
        verbose_name='Викладачі',
    )

    class Meta:
        ordering = ['course__name', 'position', 'name']
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предмети'

    def __str__(self):
        return f'{self.course.name} — {self.label}'

    @property
    def label(self):
        return f'{self.code} {self.name}' if self.code else self.name


class ScheduleEntryQuerySet(models.QuerySet):
    def proposals(self):
        return self.filter(source=ScheduleEntry.Source.TEACHER)

    def by_author(self, user):
        return self.filter(created_by=user)

    def awaiting_review(self):
        return self.filter(status=ScheduleEntry.Status.PROPOSED)

    def decided(self):
        return self.exclude(status=ScheduleEntry.Status.PROPOSED)

    def unseen_decisions(self):
        """Розглянуті пропозиції, про долю яких автор ще не дізнався."""
        return self.decided().filter(
            reviewed_at__isnull=False, author_seen_at__isnull=True,
        )


class ScheduleEntry(models.Model):
    """One slot in a group's calendar.

    Colour says who put it there and how specific it is, not how many fields
    are filled in:

    * **блакитний** — Академія забронювала день під курс (без предмета);
    * **синій** — Академія поставила предмет цієї групи;
    * **зелений** — пропозиція викладача, ще не розглянута;
    * відхилена пропозиція лишається в історії приглушеною.

    Курс, предмет і викладач не зберігаються тут — вони виводяться з групи та
    з `GroupSubject`, інакше розклад і склад групи могли б розійтися.
    """

    class Source(models.TextChoices):
        ACADEMY = 'academy', 'Академія'
        TEACHER = 'teacher', 'Викладач'

    class Status(models.TextChoices):
        PROPOSED = 'proposed', 'На розгляді'
        ACCEPTED = 'accepted', 'Прийнято'
        REJECTED = 'rejected', 'Відхилено'

    group = models.ForeignKey(
        'Group',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        verbose_name='Група',
    )
    group_subject = models.ForeignKey(
        'GroupSubject',
        on_delete=models.CASCADE,
        related_name='schedule_entries',
        null=True,
        blank=True,
        verbose_name='Предмет у групі',
        help_text='Порожньо — день заброньовано під курс цілком.',
    )
    date = models.DateField('Дата')
    start_time = models.TimeField('Початок')
    end_time = models.TimeField('Кінець')
    source = models.CharField('Джерело', max_length=10, choices=Source.choices)
    status = models.CharField(
        'Стан', max_length=10, choices=Status.choices, default=Status.ACCEPTED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_schedule_entries',
        verbose_name='Створив(ла)',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_schedule_entries',
        null=True,
        blank=True,
        verbose_name='Розглянув(ла)',
    )
    reviewed_at = models.DateTimeField('Коли розглянуто', null=True, blank=True)
    author_seen_at = models.DateTimeField(
        'Автор побачив рішення', null=True, blank=True,
        help_text='Порожньо — рішення ще не показане тому, хто пропонував.',
    )
    notes = models.TextField('Примітка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ScheduleEntryQuerySet.as_manager()

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Запис розкладу'
        verbose_name_plural = 'Записи розкладу'

    def __str__(self):
        return f'{self.date} {self.start_time}-{self.end_time} — {self.title}'

    def clean(self):
        errors = {}
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors['end_time'] = 'Час «до» має бути пізніше за час «з».'
        if self.group_subject_id and self.group_id:
            if self.group_subject.group_id != self.group_id:
                errors['group_subject'] = 'Цей предмет належить іншій групі.'
        if errors:
            raise ValidationError(errors)

    # --- усе, що виводиться з групи ------------------------------------

    @property
    def course(self):
        return self.group.course

    @property
    def subject(self):
        return self.group_subject.subject if self.group_subject_id else None

    @property
    def teacher(self):
        """Хто веде цей слот.

        Для запису Академії це викладач предмета в цій групі — окремо його не
        обирають, щоб розклад не розходився з `GroupSubject`. Для пропозиції
        без предмета це той, хто її вніс.
        """
        if self.group_subject_id:
            return self.group_subject.teacher
        if self.source == self.Source.TEACHER:
            return self.created_by
        return None

    @property
    def title(self):
        subject = self.subject
        return subject.name if subject else self.group.course.name

    @property
    def color(self):
        if self.status == self.Status.REJECTED:
            return 'rejected'
        if self.status == self.Status.PROPOSED:
            return 'green'
        return 'blue' if self.group_subject_id else 'sky'

    @property
    def is_proposal(self):
        return self.source == self.Source.TEACHER

    @property
    def awaits_review(self):
        return self.status == self.Status.PROPOSED

    @property
    def decision_is_news(self):
        """Рішення вже є, а той, хто пропонував, його ще не бачив."""
        return self.reviewed_at is not None and self.author_seen_at is None


class DatedRange(models.Model):
    """Shared date range for everything that touches a group.

    Group, GroupSubject and Enrollment all answer the same question — «коли?» —
    so the period, its status and its label live in one place.
    """

    start_date = models.DateField('Початок')
    end_date = models.DateField('Завершення', null=True, blank=True)

    STATUS_LABELS = {
        'planned': 'Заплановано',
        'active': 'Триває',
        'finished': 'Завершено',
    }

    class Meta:
        abstract = True

    def status(self, on=None):
        on = on or dt.date.today()
        if self.start_date > on:
            return 'planned'
        if self.end_date and self.end_date < on:
            return 'finished'
        return 'active'

    @property
    def status_label(self):
        return self.STATUS_LABELS[self.status()]

    def is_active(self, on=None):
        return self.status(on) == 'active'

    def clean_dates(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            return {'end_date': 'Завершення не може бути раніше за початок.'}
        return {}


class GroupQuerySet(models.QuerySet):
    def active(self, on=None):
        """Groups whose study period covers `on` (today by default)."""
        on = on or dt.date.today()
        return self.filter(start_date__lte=on).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=on)
        )

    def for_teacher(self, user):
        return self.filter(group_subjects__teacher=user).distinct()

    def for_student(self, user):
        return self.filter(enrollments__student=user).distinct()

    def for_person(self, user):
        """Every group this person belongs to, in any capacity.

        Roles add up rather than replace each other: a graduate who joins the
        staff is still the person who studied here, and must keep their own
        group — and everything in it — after «викладач» is added to their
        roles. Asking «teacher or student?» and branching would quietly take
        their alma mater away.
        """
        return self.filter(
            models.Q(group_subjects__teacher=user) | models.Q(enrollments__student=user)
        ).distinct()

    def annotate_my_part(self, user):
        """Mark, per group, whether this person teaches in it, studies in it, or both."""
        return self.annotate(
            i_teach=models.Exists(
                GroupSubject.objects.filter(group=models.OuterRef('pk'), teacher=user)
            ),
            i_study=models.Exists(
                Enrollment.objects.filter(group=models.OuterRef('pk'), student=user)
            ),
        )


class Group(DatedRange):
    """A cohort studying exactly one course over a fixed period.

    The group is the only place where people meet a course: a teacher teaches
    a subject *in a group*, a student studies *in a group*. Nothing links a
    teacher or a student to a course directly.
    """

    name = models.CharField('Назва групи', max_length=200, unique=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='groups',
        verbose_name='Курс',
    )
    start_date = models.DateField('Початок навчання')
    end_date = models.DateField('Завершення навчання', null=True, blank=True)
    notes = models.TextField('Примітка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = GroupQuerySet.as_manager()

    class Meta:
        ordering = ['-start_date', 'name']
        verbose_name = 'Група'
        verbose_name_plural = 'Групи'

    def __str__(self):
        return self.name

    def clean(self):
        errors = self.clean_dates()
        if errors:
            raise ValidationError(errors)

    @property
    def subjects(self):
        """Subjects actually taught in this group (a subset of the course's)."""
        return Subject.objects.filter(group_subjects__group=self).distinct()

    @property
    def teachers(self):
        return get_user_model().objects.filter(group_subjects__group=self).distinct()

    @property
    def students(self):
        return get_user_model().objects.filter(enrollments__group=self).distinct()


class DatedLinkQuerySet(models.QuerySet):
    """Shared `active()` for the group link tables — both carry a date range."""

    def active(self, on=None):
        on = on or dt.date.today()
        return self.filter(start_date__lte=on).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=on)
        )


class GroupSubjectQuerySet(DatedLinkQuerySet):
    def for_teacher(self, user):
        return self.filter(teacher=user)

    def for_student(self, user):
        return self.filter(group__enrollments__student=user).distinct()


class GroupSubject(DatedRange):
    """One subject as taught in one group, by exactly one teacher.

    The link itself is the fact — it is deliberately not validated against
    `User.role`. Roles change (a former student becomes a teacher), and a role
    check here would retroactively invalidate history that already happened.
    Forms and the admin offer the right people; the model records reality.

    The same subject in another group may have a different teacher — that is
    why the teacher lives here and not on `Subject`. A change of teacher
    mid-course is recorded by closing this row's date range and opening a new
    one, not by overwriting the teacher.
    """

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='group_subjects',
        verbose_name='Група',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='group_subjects',
        verbose_name='Предмет',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='group_subjects',
        verbose_name='Викладач',
    )
    objects = GroupSubjectQuerySet.as_manager()

    class Meta:
        ordering = ['group', 'start_date', 'subject__name']
        verbose_name = 'Предмет у групі'
        verbose_name_plural = 'Предмети у групах'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'subject', 'start_date'],
                name='unique_group_subject_period',
            ),
        ]

    def __str__(self):
        return f'{self.group.name} — {self.subject.name} ({self.teacher})'

    def clean(self):
        errors = self.clean_dates()
        if self.subject_id and self.group_id:
            if self.subject.course_id != self.group.course_id:
                errors['subject'] = 'Предмет не належить курсу цієї групи.'
        if errors:
            raise ValidationError(errors)


class EnrollmentQuerySet(DatedLinkQuerySet):
    def for_teacher(self, user):
        """Enrollments in every group where this teacher teaches something."""
        return self.filter(group__group_subjects__teacher=user).distinct()


class Enrollment(DatedRange):
    """A student's membership in a group, over a date range.

    As with `GroupSubject`, the row is not validated against `User.role`: a
    graduate who later joins the staff must keep the record of having studied.

    A student may be enrolled in several groups at once (different courses in
    parallel); `end_date` empty means they are still studying.
    """

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Група',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Студент',
    )
    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        ordering = ['group', 'student__last_name', 'student__first_name']
        verbose_name = 'Студент у групі'
        verbose_name_plural = 'Студенти у групах'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'student', 'start_date'],
                name='unique_enrollment_period',
            ),
        ]

    def __str__(self):
        return f'{self.student} — {self.group.name}'

    def clean(self):
        errors = self.clean_dates()
        if errors:
            raise ValidationError(errors)


def teacher_students(teacher, on=None):
    """Students a teacher actually has — via the groups where they teach."""
    qs = Enrollment.objects.for_teacher(teacher)
    if on is not False:
        qs = qs.active(on)
    return get_user_model().objects.filter(enrollments__in=qs).distinct()


def student_teachers(student, on=None):
    """Teachers a student actually has — via the subjects of their groups."""
    qs = GroupSubject.objects.for_student(student)
    if on is not False:
        qs = qs.active(on)
    return get_user_model().objects.filter(group_subjects__in=qs).distinct()
