from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import LoginForm, UserCreateForm, UserRoleForm
from .mixins import UserManagementRequiredMixin
from .models import User


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


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
