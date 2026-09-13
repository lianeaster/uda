import datetime as dt

from django import forms

from accounts.models import User

from .models import Course, ScheduleEntry, Subject
from .services import DAY_END_HOUR, DAY_START_HOUR

FROM_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR, DAY_END_HOUR)]
TO_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR + 1, DAY_END_HOUR + 1)]


class SubjectSelect(forms.Select):
    """Renders each <option> with a data-course attribute so the schedule
    popup can filter subjects down to the currently chosen course in JS."""

    def __init__(self, *args, course_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.course_map = course_map or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            course_id = self.course_map.get(int(str(value)))
            if course_id:
                option['attrs']['data-course'] = str(course_id)
        return option


class ScheduleEntryForm(forms.ModelForm):
    start_hour = forms.ChoiceField(label='Час з', choices=FROM_CHOICES)
    end_hour = forms.ChoiceField(label='Час до', choices=TO_CHOICES)

    class Meta:
        model = ScheduleEntry
        fields = ['date', 'course', 'teacher', 'subject', 'notes']
        labels = {
            'date': 'Дата',
            'course': 'Курс',
            'teacher': 'Викладач (ПІБ)',
            'subject': 'Предмет',
            'notes': 'Примітка',
        }
        widgets = {
            'date': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if actor is not None and actor.is_teacher:
            self.fields.pop('teacher')
            self.fields.pop('course')
            self.fields['subject'].required = True
            self.fields['subject'].queryset = actor.subjects.select_related('course').all()
            self.fields['subject'].empty_label = 'Оберіть предмет'
        else:
            self.fields['course'].required = True
            self.fields['course'].empty_label = 'Оберіть курс'

            self.fields['teacher'].queryset = User.objects.filter(role=User.Role.TEACHER)
            self.fields['teacher'].required = False
            self.fields['teacher'].empty_label = '— без викладача —'

            self.fields['subject'].required = False
            course_map = dict(Subject.objects.values_list('pk', 'course_id'))
            self.fields['subject'].widget = SubjectSelect(course_map=course_map)
            self.fields['subject'].queryset = Subject.objects.select_related('course').all()
            self.fields['subject'].empty_label = '— без предмету —'

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
        is_new = instance.created_by_id is None
        if is_new:
            instance.created_by = self.actor
        instance.start_time = self.cleaned_data['start_time']
        instance.end_time = self.cleaned_data['end_time']
        if self.actor.is_teacher:
            instance.teacher = self.actor
            # Only stamp `source` on creation — a teacher editing a booking a
            # manager assigned to them shouldn't silently take Academy
            # ownership away from the manager who can still manage it.
            if is_new:
                instance.source = ScheduleEntry.Source.TEACHER
            instance.course = instance.subject.course
            instance.title = instance.subject.name
        else:
            if is_new:
                instance.source = ScheduleEntry.Source.ACADEMY
            if instance.subject:
                instance.course = instance.subject.course
                instance.title = instance.subject.name
            else:
                instance.title = instance.course.name
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
        self.fields['teachers'].queryset = User.objects.filter(role=User.Role.TEACHER)
