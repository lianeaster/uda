from django import forms

from schedule.forms import date_input

from .models import Task


class TaskForm(forms.ModelForm):
    """Нова задача у своєму календарі. Хто керує, може поставити її на все керування."""

    shared = forms.BooleanField(
        label='Спільна для керування', required=False,
        help_text='Побачать усі менеджери й супер-адміни; виконав один — закрита для всіх.',
    )

    class Meta:
        model = Task
        fields = ['title', 'due_date', 'remind_on', 'notes']
        widgets = {
            'due_date': date_input(),
            'remind_on': date_input(),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields['remind_on'].required = False
        if not actor.can_manage_users:
            del self.fields['shared']

    def clean(self):
        cleaned = super().clean()
        due, remind = cleaned.get('due_date'), cleaned.get('remind_on')
        if due and remind and remind > due:
            self.add_error('remind_on', 'Нагадування не може бути пізніше за термін.')
        return cleaned

    def save(self, commit=True):
        task = super().save(commit=False)
        task.created_by = self.actor
        task.assignee = None if self.cleaned_data.get('shared') else self.actor
        if commit:
            task.save()
        return task
