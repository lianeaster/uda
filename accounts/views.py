from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import (
    AccountForm,
    AccountPasswordChangeForm,
    LoginForm,
    UserCreateForm,
    UserRoleForm,
)
from .mixins import UserManagementRequiredMixin
from .models import User


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class PersonListView(LoginRequiredMixin, ListView):
    """Картки, які видно саме цій людині (`User.objects.visible_to`).

    Фільтр — за родом людей; студентів можна ще звузити до групи. Групи в
    списку — ті, що людині видно й на сторінці груп. Фільтри лише звужують
    видиме, нових карток вони не відкривають.
    """

    template_name = 'accounts/person_list.html'
    context_object_name = 'people'

    # Керівництво — одним пунктом: для того, хто шукає людину, супер-адмін і
    # менеджер однаково «з адміністрації».
    ROLE_FILTERS = {
        'student': ('Студенти', [User.Role.STUDENT]),
        'teacher': ('Викладачі', [User.Role.TEACHER]),
        'manager': ('Менеджери', [User.Role.MANAGER, User.Role.SUPER_ADMIN]),
    }

    def role(self):
        role = self.request.GET.get('role', '')
        return role if role in self.ROLE_FILTERS else ''

    def group_choices(self):
        from schedule.models import Group

        user = self.request.user
        groups = Group.objects.all() if user.can_manage_users else Group.objects.for_person(user)
        return groups.select_related('course').order_by('-start_date', 'name')

    def group(self):
        if self.role() != 'student':
            return None
        requested = self.request.GET.get('group', '')
        if not requested.isdigit():
            return None
        return self.group_choices().filter(pk=requested).first()

    def get_queryset(self):
        people = User.objects.visible_to(self.request.user).with_roles()
        role = self.role()
        if role:
            people = people.filter(role_links__role__in=self.ROLE_FILTERS[role][1]).distinct()
        group = self.group()
        if group is not None:
            people = people.filter(enrollments__group=group).distinct()
        return people

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.role()
        context['role_filters'] = [(value, label) for value, (label, _) in self.ROLE_FILTERS.items()]
        context['current_role'] = role
        context['current_group'] = self.group()
        context['groups'] = self.group_choices() if role == 'student' else None
        context['filtered'] = bool(role)
        return context


class PersonDetailView(LoginRequiredMixin, DetailView):
    """Чужа картка. Невидиму не ховаємо напівдорозі — її просто немає (404)."""

    template_name = 'accounts/person_detail.html'
    context_object_name = 'person'

    def get_queryset(self):
        return User.objects.visible_to(self.request.user).with_roles()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.object
        context['is_self'] = person.pk == self.request.user.pk
        context['can_edit_account'] = self.request.user.can_edit_user(person)
        return context


class AccountView(LoginRequiredMixin, UpdateView):
    """Свої налаштування — єдина сторінка, яку відкриває будь-яка роль.

    Об'єкт тут завжди `request.user`: власну картку не шукають за pk, тож
    підставити чужий і не вийде.
    """

    form_class = AccountForm
    template_name = 'accounts/account.html'
    success_url = reverse_lazy('accounts:account')

    def get_object(self, queryset=None):
        user = self.request.user
        # Ім'я старого файлу потрібне вже після збереження, коли поле вказує
        # на новий, — тож запам'ятовуємо його тут.
        self.photo_before = user.photo.name
        return user

    def form_valid(self, form):
        response = super().form_valid(form)
        # Storage не перезаписує файли, а додає суфікс, тож кожне нове фото
        # лишало б попереднє висіти в media назавжди.
        if self.photo_before and self.photo_before != self.object.photo.name:
            self.object.photo.storage.delete(self.photo_before)
        messages.success(self.request, 'Картку оновлено.')
        return response


class PasswordChangeView(auth_views.PasswordChangeView):
    """Django сам вимагає поточний пароль і не розлогінює після зміни."""

    form_class = AccountPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:account')

    def form_valid(self, form):
        messages.success(self.request, 'Пароль змінено.')
        return super().form_valid(form)


class UserListView(UserManagementRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        # Сортування й пошук по колонках робить сама таблиця
        # (`static/js/table.js`). Тут лишається фільтр ролі: на нього ведуть
        # тайли кабінету, тож він має переживати перезавантаження й посилання.
        queryset = User.objects.with_roles()
        role = self.request.GET.get('role')
        if role in User.Role.values:
            queryset = queryset.with_role(role)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_role'] = self.request.GET.get('role', '')
        context['role_choices'] = User.Role.choices
        return context


class UserCreateView(UserManagementRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Користувача «{form.instance.username}» створено.')
        return super().form_valid(form)


class UserUpdateView(UserManagementRequiredMixin, UpdateView):
    model = User
    form_class = UserRoleForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_queryset(self):
        return User.objects.all()

    def test_func(self):
        if not super().test_func():
            return False
        target = self.get_object()
        return self.request.user.can_edit_user(target)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Дані користувача «{form.instance.username}» оновлено.')
        return super().form_valid(form)


class UserDeleteView(UserManagementRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if not request.user.can_edit_user(target) or target.pk == request.user.pk:
            messages.error(request, 'У вас немає прав видалити цього користувача.')
            return redirect('accounts:user_list')
        target.delete()
        messages.success(request, f'Користувача «{target.username}» видалено.')
        return redirect('accounts:user_list')
