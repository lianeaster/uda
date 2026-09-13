from django import forms

from .models import ContactRequest


class ContactRequestForm(forms.ModelForm):
    consent = forms.BooleanField(label='Погоджуюсь з політикою конфіденційності', required=True)

    class Meta:
        model = ContactRequest
        fields = ['name', 'phone', 'email', 'interest']
        labels = {
            'name': "Ім'я",
            'phone': 'Телефон',
            'email': 'Email',
            'interest': 'Що вас цікавить',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': "Ваше ім'я"}),
            'phone': forms.TextInput(attrs={'type': 'tel', 'placeholder': '+380'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@mail.com'}),
            'interest': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Курс, консультація, власна дистилерія…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['interest'].required = False
