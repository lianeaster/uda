from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Логін', widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role']
        labels = {
            'username': 'Логін',
            'first_name': "Ім'я",
            'last_name': 'Прізвище',
            'email': 'Email',
            'role': 'Роль',
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if actor is not None:
            self.fields['role'].choices = actor.assignable_roles

    def clean_role(self):
        role = self.cleaned_data['role']
        if self.actor is not None and not self.actor.can_assign_role(role):
            raise forms.ValidationError('У вас немає прав призначати цю роль.')
        return role


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'is_active']
        labels = {
            'first_name': "Ім'я",
            'last_name': 'Прізвище',
            'email': 'Email',
            'role': 'Роль',
            'is_active': 'Активний',
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if actor is not None:
            choices = set(actor.assignable_roles)
            if self.instance and self.instance.role:
                choices.add((self.instance.role, dict(User.Role.choices)[self.instance.role]))
            self.fields['role'].choices = sorted(choices)

    def clean_role(self):
        role = self.cleaned_data['role']
        if self.actor is not None and role != self.instance.role and not self.actor.can_assign_role(role):
            raise forms.ValidationError('У вас немає прав призначати цю роль.')
        return role
