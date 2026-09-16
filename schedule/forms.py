import datetime as dt

from django import forms

from accounts.models import User

from .models import Course, GroupSubject, ScheduleEntry, Subject
from .services import DAY_END_HOUR, DAY_START_HOUR

FROM_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR, DAY_END_HOUR)]
TO_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR + 1, DAY_END_HOUR + 1)]


class ScheduleEntryForm(forms.ModelForm):
    """Booking a slot in one group's calendar.

    The group comes from the calendar being viewed, not from a field, and the
    teacher is never picked here — it follows from the subject in that group.
    Management may leave the subject empty to hold the whole day for the
    course; a teacher always proposes a slot for a subject they actually teach.
    """

    start_hour = forms.ChoiceField(label='Час з', choices=FROM_CHOICES)
    end_hour = forms.ChoiceField(label='Час до', choices=TO_CHOICES)

    class Meta:
        model = ScheduleEntry
        fields = ['date', 'group_subject', 'notes']
        labels = {
            'date': 'Дата',
            'group_subject': 'Предмет',
            'notes': 'Примітка',
        }
        widgets = {
            'date': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, actor=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.group = group or (self.instance.group if self.instance.pk else None)

        subjects = self.group.group_subjects.select_related('subject', 'teacher')
        field = self.fields['group_subject']
        if self.proposing:
            field.queryset = subjects.filter(teacher=actor)
            field.required = True
            field.empty_label = 'Оберіть предмет'
        else:
            field.queryset = subjects
            field.required = False
            field.empty_label = '— увесь день під курс —'

    @property
    def proposing(self):
        """A teacher who does not also manage can only ever propose."""
        return self.actor is not None and self.actor.teaches_only

    def clean(self):
        cleaned = super().clean()
        start_hour, end_hour = cleaned.get('start_hour'), cleaned.get('end_hour')
        if start_hour and end_hour:
            start_hour, end_hour = int(start_hour), int(end_hour)
            if end_hour <= start_hour:
                raise forms.ValidationError('Час «до» має бути пізніше за час «з».')
            cleaned['start_time'] = dt.time(start_hour)
            cleaned['end_time'] = dt.time(end_hour)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.pk is None:
            instance.created_by = self.actor
            instance.group = self.group
            # Хто вніс запис, той і визначає його природу: пропозиція викладача
            # чекає на розгляд, запис менеджменту одразу чинний.
            if self.proposing:
                instance.source = ScheduleEntry.Source.TEACHER
                instance.status = ScheduleEntry.Status.PROPOSED
            else:
                instance.source = ScheduleEntry.Source.ACADEMY
                instance.status = ScheduleEntry.Status.ACCEPTED
        instance.start_time = self.cleaned_data['start_time']
        instance.end_time = self.cleaned_data['end_time']
        if commit:
            instance.save()
        return instance


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name']
        labels = {'name': 'Назва курсу'}


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'course', 'teachers']
        labels = {'name': 'Назва предмету', 'course': 'Курс', 'teachers': 'Викладачі'}
        widgets = {'teachers': forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teachers'].queryset = User.objects.with_role(User.Role.TEACHER)


class GroupSubjectForm(forms.ModelForm):
    """Ставить предмет курсу в конкретну групу й закріплює за ним викладача.

    Предмети обмежені курсом групи й ті, яких у ній ще немає: один предмет
    у групі веде рівно один викладач, і двічі додати його не можна.
    """

    class Meta:
        model = GroupSubject
        fields = ['subject', 'teacher', 'start_date', 'end_date']
        labels = {
            'subject': 'Предмет',
            'teacher': 'Викладач',
            'start_date': 'Початок вивчення',
            'end_date': 'Завершення',
        }
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group
        self.instance.group = group

        taken = group.group_subjects.values_list('subject_id', flat=True)
        self.fields['subject'].queryset = (
            group.course.subjects.exclude(pk__in=taken).order_by('position', 'name')
        )
        self.fields['subject'].empty_label = 'Оберіть предмет'
        self.fields['teacher'].queryset = User.objects.with_role(User.Role.TEACHER)
        self.fields['teacher'].empty_label = 'Оберіть викладача'
        self.fields['start_date'].initial = group.start_date
        self.fields['end_date'].initial = group.end_date
        self.fields['end_date'].required = False
