import datetime as dt

from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User

from .models import (
    Course, CourseSubject, Enrollment, Group, GroupSubject, Module, ScheduleEntry, Subject,
)
from .services import DAY_END_HOUR, DAY_START_HOUR

FROM_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR, DAY_END_HOUR)]
TO_CHOICES = [(h, f'{h}:00') for h in range(DAY_START_HOUR + 1, DAY_END_HOUR + 1)]


def date_input():
    """Календар браузера. Формат — ISO явно: локалізований «d.m.Y» поле
    type=date не прочитає й покаже порожнім, навіть коли дата є."""
    return forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')


class RepeatSelect(forms.SelectMultiple):
    """Кілька значень як стовпчик випадних списків із «+ ще один».

    Довгий перелік прапорців змушує шукати очима потрібне ім'я серед усіх;
    тут людина додає рядок і обирає зі списку. Усі списки мають одне ім'я,
    тож на сервер приходить звичайний перелік значень; порожні (рядок додали,
    але нічого не обрали) і повтори відкидаються.
    """

    template_name = 'schedule/widgets/repeat_select.html'

    def __init__(self, add_label='Додати', empty_label='— оберіть —', attrs=None):
        super().__init__(attrs)
        self.add_label = add_label
        self.empty_label = empty_label

    def value_from_datadict(self, data, files, name):
        values = super().value_from_datadict(data, files, name) or []
        return list(dict.fromkeys(v for v in values if v))

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        selected = [str(v) for v in (value or []) if v not in (None, '')]
        context['widget'].update({
            'options': [(str(v), label) for v, label in self.choices if v != ''],
            'rows': selected or [''],
            'add_label': self.add_label,
            'empty_label': self.empty_label,
        })
        return context


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
        fields = ['name', 'description', 'group_price_eur', 'excursion_price']
        labels = {'name': 'Назва курсу', 'description': 'Опис'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['course', 'code', 'name', 'format']
        labels = {'code': 'Номер у програмі'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].empty_label = 'Оберіть курс'


class SubjectForm(forms.ModelForm):
    """Предмет із викладачами. Курси, у програмах яких він стоїть, — окремим
    набором рядків (`CourseSubjectFormSet`): у кожного курсу свій номер."""

    class Meta:
        model = Subject
        fields = ['name', 'teachers']
        labels = {'name': 'Назва предмету', 'teachers': 'Викладачі'}
        widgets = {'teachers': RepeatSelect(add_label='Додати викладача',
                                            empty_label='Оберіть викладача')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teachers'].queryset = User.objects.with_role(User.Role.TEACHER)
        self.fields['teachers'].help_text = ''


class CourseSubjectForm(forms.ModelForm):
    class Meta:
        model = CourseSubject
        fields = ['course', 'code', 'module', 'hours']
        labels = {'course': 'Курс', 'code': '№ у програмі', 'module': 'Модуль', 'hours': 'Годин'}
        widgets = {
            'course': forms.Select(attrs={'aria-label': 'Курс'}),
            'code': forms.TextInput(attrs={'placeholder': '№',
                                           'aria-label': 'Номер у програмі курсу'}),
            'module': forms.Select(attrs={'aria-label': 'Модуль'}),
            'hours': forms.NumberInput(attrs={'placeholder': 'год', 'step': '0.5', 'min': '0',
                                              'aria-label': 'Годин у програмі курсу'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].empty_label = 'Оберіть курс'
        # Модулі всіх курсів одним списком, із назвою курсу; чужий модуль
        # відсіює `CourseSubject.clean`.
        self.fields['module'].queryset = Module.objects.select_related('course')
        self.fields['module'].empty_label = 'Оберіть модуль'
        # У програмі курсу предмет завжди стоїть у модулі.
        self.fields['module'].required = True


def course_subject_formset(subject=None, data=None, module=None):
    """Рядки «курс + номер + модуль + години» для форми предмета.

    Порожній рядок показуємо, лише коли курсів іще немає, — щоб було куди
    вписати перший (з картки модуля він приходить уже з курсом і модулем).
    Незаповнений рядок формсет просто пропускає.
    """
    has_links = subject is not None and subject.pk and subject.course_links.exists()
    formset_class = forms.inlineformset_factory(
        Subject, CourseSubject, form=CourseSubjectForm,
        extra=0 if has_links else 1, can_delete=True,
    )
    initial = ([{'course': module.course_id, 'module': module.pk}]
               if module is not None and not has_links else None)
    return formset_class(data, instance=subject, prefix='courses', initial=initial)


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'course', 'start_date', 'end_date', 'notes']
        labels = {
            'name': 'Назва групи',
            'course': 'Курс',
            'start_date': 'Початок навчання',
            'end_date': 'Завершення навчання',
            'notes': 'Примітка',
        }
        help_texts = {'end_date': 'Порожньо — група ще навчається, дата завершення невідома.'}
        widgets = {
            'start_date': date_input(),
            'end_date': date_input(),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].empty_label = 'Оберіть курс'


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
            'start_date': date_input(),
            'end_date': date_input(),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.group = group
        self.instance.group = group

        taken = group.group_subjects.values_list('subject_id', flat=True)
        self.fields['subject'].queryset = (
            Subject.objects.filter(course_links__course=group.course)
            .exclude(pk__in=taken).order_by('course_links__position', 'name')
        )
        self.fields['subject'].empty_label = 'Оберіть предмет'
        self.fields['teacher'].queryset = User.objects.with_role(User.Role.TEACHER)
        self.fields['teacher'].empty_label = 'Оберіть викладача'
        self.fields['start_date'].initial = group.start_date
        self.fields['end_date'].initial = group.end_date
        self.fields['end_date'].required = False


class EnrollmentForm(forms.ModelForm):
    """Навчання студента в одній групі.

    Дати можна не вписувати: початок тоді береться з групи, а для нового
    зарахування — і завершення. Студента в режимі «новий» тут не обирають —
    його створює `NewStudentForm`, і вже потім до нього прив'язується рядок.
    """

    class Meta:
        model = Enrollment
        fields = ['student', 'group', 'start_date', 'end_date']
        labels = {
            'student': 'Студент',
            'group': 'Група',
            'start_date': 'Початок навчання в групі',
            'end_date': 'Завершення',
        }
        help_texts = {'start_date': 'Порожньо — з початку навчання групи.'}
        widgets = {'start_date': date_input(), 'end_date': date_input()}

    def __init__(self, *args, student_required=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.with_role(User.Role.STUDENT)
        self.fields['student'].required = student_required
        self.fields['student'].empty_label = 'Оберіть студента'
        # Студента в наявному рядку не міняють — інакше це вже інше зарахування.
        self.fields['student'].disabled = bool(self.instance.pk)
        self.fields['group'].queryset = Group.objects.select_related('course')
        self.fields['group'].empty_label = 'Оберіть групу'
        self.fields['start_date'].required = False
        self.fields['end_date'].help_text = (
            'Порожньо — студент ще навчається.' if self.instance.pk
            else 'Порожньо — коли завершує група.'
        )

    def clean(self):
        cleaned = super().clean()
        group = cleaned.get('group')
        if group:
            if not cleaned.get('start_date'):
                cleaned['start_date'] = group.start_date
            if not self.instance.pk and not cleaned.get('end_date'):
                cleaned['end_date'] = group.end_date
        return cleaned


class NewStudentForm(UserCreationForm):
    """Обліковий запис для нового студента — роль ставиться сама."""

    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'patronymic', 'email', 'username']
        labels = {
            'last_name': 'Прізвище',
            'first_name': "Ім'я",
            'email': 'Email',
            'username': 'Логін',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['username'].help_text = ''

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.set_roles([User.Role.STUDENT])
        return user


class StudentInfoForm(forms.ModelForm):
    """ПІБ і пошта студента — поруч із його навчанням у групі."""

    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'patronymic', 'email']
        labels = {'last_name': 'Прізвище', 'first_name': "Ім'я", 'email': 'Email'}
