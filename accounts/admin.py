from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'roles_display', 'is_active', 'is_staff')
    list_filter = ('role_links__role', 'is_active', 'is_staff')
    inlines = (UserRoleInline,)
    # Картку «Про мене» людина заповнює сама, але супер-адмін мусить мати
    # доступ і тут — щоб виправити чуже фото або текст на прохання.
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Картка «Про мене»',
         {'fields': ('patronymic', 'photo', 'about', 'education', 'interests', 'experience')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).with_roles()

    @admin.display(description='Ролі')
    def roles_display(self, obj):
        return ', '.join(label for _, label in obj.role_labels) or '—'
