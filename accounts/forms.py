from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Логін', widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class RolesFieldMixin:
    """Ролі — набір, тож у формі це прапорці, а не список із одним вибором.

    Показуємо лише ті ролі, які актор має право надавати, плюс ті, що вже є в
    людини: інакше менеджер, відкривши чужу картку, мовчки зняв би роль, якої
    сам призначити не може.
    """

    def setup_roles(self, actor, instance=None):
        # Поле створюється тут, а не оголошується в класі: метаклас форм Django
        # збирає поля лише з самої форми та з баз, що вже є формами, тож
        # оголошене на звичайному міксині воно просто загубилося б.
        self.actor = actor
        current = set(instance.roles) if instance and instance.pk else set()
        allowed = {value for value, _ in actor.assignable_roles} if actor else set(User.Role.values)
        self.locked = current - allowed

        labels = dict(User.Role.choices)
        self.fields['roles'] = forms.MultipleChoiceField(
            label='Ролі',
            choices=[(value, labels[value]) for value in User.Role.values
                     if value in allowed or value in current],
            widget=forms.CheckboxSelectMultiple,
            required=True,
            initial=sorted(current),
        )

    def clean_roles(self):
        roles = set(self.cleaned_data['roles'])
        if self.actor is None:
            return sorted(roles)
        # Ролі, які актор не може надавати, він і не може зняти — повертаємо їх.
        roles |= self.locked
        for role in roles - self.locked:
            if not self.actor.can_assign_role(role):
                raise forms.ValidationError('У вас немає прав призначати цю роль.')
        return sorted(roles)

    def save_roles(self, user):
        user.set_roles(self.cleaned_data['roles'])


class UserCreateForm(RolesFieldMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username': 'Логін',
            'first_name': "Ім'я",
            'last_name': 'Прізвище',
            'email': 'Email',
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_roles(actor)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self.save_roles(user)
        return user


class UserRoleForm(RolesFieldMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        labels = {
            'first_name': "Ім'я",
            'last_name': 'Прізвище',
            'email': 'Email',
            'is_active': 'Активний',
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_roles(actor, self.instance)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self.save_roles(user)
        return user
