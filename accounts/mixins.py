from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Base mixin: subclasses implement `allowed_roles` or override `test_func`."""

    allowed_roles: tuple = ()
    raise_exception = False
    permission_denied_message = 'У вас немає доступу до цієї сторінки.'

    def test_func(self):
        user = self.request.user
        # Ролі — набір: достатньо мати хоч одну з дозволених.
        return user.is_authenticated and bool(user.roles & set(self.allowed_roles))

    def handle_no_permission(self):
        from django.contrib import messages
        from django.shortcuts import redirect

        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
            return redirect('dashboard:home')
        return super().handle_no_permission()


class UserManagementRequiredMixin(RoleRequiredMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_manage_users
