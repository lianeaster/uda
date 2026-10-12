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


class ConstructorRequestForm(ContactRequestForm):
    """Запис на курс із конструктора: та сама заявка плюс те, що він підібрав.

    `interest` (обраний курс) і `details` (відповіді й програма) заповнює
    сторінка, людина їх не бачить. `state` у базу не йде — це відповіді в
    стислому вигляді, щоб після помилки у формі показати той самий результат.
    """

    state = forms.CharField(required=False, max_length=600, widget=forms.HiddenInput)

    class Meta(ContactRequestForm.Meta):
        fields = ['name', 'phone', 'email', 'interest', 'details']
        widgets = {
            **ContactRequestForm.Meta.widgets,
            'interest': forms.HiddenInput,
            'details': forms.HiddenInput,
        }

    def clean_details(self):
        # Текст складає скрипт, але надіслати можна будь-що — обрізаємо.
        return self.cleaned_data['details'][:4000]

    def save(self, commit=True):
        self.instance.source = ContactRequest.Source.CONSTRUCTOR
        if not self.instance.interest:
            self.instance.interest = 'Конструктор курсів'
        return super().save(commit)
