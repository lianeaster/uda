from django import forms

from core.forms import ContactRequestForm
from core.models import ContactRequest

from .pages import TOPICS


class CenterContactForm(ContactRequestForm):
    """Звернення до Центру зі сторінки «Контакти».

    Окрім спільних полів, питає компанію, тему зі списку (`pages.TOPICS`,
    лягає в `interest`) і опис завдання своїми словами (у `details`).
    """

    interest = forms.ChoiceField(
        label='Що вас цікавить?', required=False,
        choices=[('', 'Оберіть тему')] + [(label, label) for _, label in TOPICS],
    )

    class Meta(ContactRequestForm.Meta):
        fields = ['name', 'company', 'email', 'phone', 'interest', 'details']
        labels = {
            **ContactRequestForm.Meta.labels,
            'name': "Ваше ім'я",
            'company': 'Компанія або організація',
            'email': 'Електронна пошта',
            'details': 'Коротко опишіть ваше завдання',
        }
        widgets = {
            **ContactRequestForm.Meta.widgets,
            'company': forms.TextInput(attrs={'placeholder': 'Необов\'язково'}),
            'details': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Яка сировина, який продукт хочете отримати, '
                               'що вже зроблено…',
            }),
        }

    def clean_details(self):
        return self.cleaned_data['details'][:4000]

    def save(self, commit=True):
        self.instance.source = ContactRequest.Source.CENTER
        return super().save(commit)


class FoodAcademyContactForm(ContactRequestForm):
    """Заявка з харчової академії: напрям і чи людина хоче вчитися, чи викладати."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interest'].label = 'Який напрям цікавить'
        self.fields['interest'].widget.attrs['placeholder'] = (
            'Снеки, соуси, ферментація… Хочу вчитися чи викладати'
        )

    def save(self, commit=True):
        self.instance.source = ContactRequest.Source.FOOD_ACADEMY
        return super().save(commit)
