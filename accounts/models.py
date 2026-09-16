from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    def with_role(self, role):
        return self.filter(role_links__role=role).distinct()

    def with_roles(self):
        """Prefetch the role set so `user.roles` costs no extra query per row."""
        return self.prefetch_related('role_links')


class UserAccountManager(UserManager.from_queryset(UserQuerySet)):
    """`UserManager` keeps `create_user` / `createsuperuser` working."""

    def create_user(self, *args, roles=(), **kwargs):
        user = super().create_user(*args, **kwargs)
        if roles:
            user.set_roles(roles)
        return user

    def create_superuser(self, *args, roles=None, **kwargs):
        """`manage.py createsuperuser` must produce a usable super-admin.

        Roles no longer have a column default, so without this the first
        account would be created with an empty role set and locked out of
        everything the platform gates on roles.
        """
        user = super().create_superuser(*args, **kwargs)
        user.set_roles(roles if roles is not None else [User.Role.SUPER_ADMIN])
        return user


class User(AbstractUser):
    """Custom user whose roles drive access across the whole platform.

    Roles are a set, not one value. Most people have exactly one, but the same
    person can be both a manager and a teacher, and roles change over time —
    a graduate can join the staff. Historical links (`Enrollment`,
    `GroupSubject`) are therefore never validated against the current role set.
    """

    class Role(models.TextChoices):
        # Порядок визначає старшинство: перший — найповажніший.
        SUPER_ADMIN = 'super_admin', 'Супер-адмін'
        MANAGER = 'manager', 'Менеджер'
        TEACHER = 'teacher', 'Викладач'
        STUDENT = 'student', 'Студент'

    objects = UserAccountManager()

    class Meta(AbstractUser.Meta):
        ordering = ['last_name', 'first_name', 'username']

    def __str__(self):
        full_name = self.get_full_name()
        return full_name or self.username

    @property
    def initials(self):
        parts = [p[0].upper() for p in (self.first_name, self.last_name) if p]
        if parts:
            return ''.join(parts)
        return (self.username[:2] or '??').upper()

    # --- ролі ---------------------------------------------------------

    @property
    def roles(self):
        if not hasattr(self, '_roles_cache'):
            self._roles_cache = {link.role for link in self.role_links.all()}
        return self._roles_cache

    @property
    def ordered_roles(self):
        """Roles from the most privileged down — the order they are shown in."""
        return [value for value in self.Role.values if value in self.roles]

    @property
    def primary_role(self):
        """The most privileged role; what a single badge or colour keys off."""
        ordered = self.ordered_roles
        return ordered[0] if ordered else ''

    @property
    def role_rank(self):
        """Позиція найповажнішої ролі — щоб таблиця сортувала за старшинством,
        а не за абеткою коду (де «manager» став би вище за «super_admin»)."""
        ordered = self.ordered_roles
        return self.Role.values.index(ordered[0]) if ordered else len(self.Role.values)

    @property
    def role_labels(self):
        labels = dict(self.Role.choices)
        return [(value, labels[value]) for value in self.ordered_roles]

    def has_role(self, role):
        return role in self.roles

    def set_roles(self, roles):
        """Replace the role set. Unknown codes are ignored."""
        wanted = {r for r in roles if r in self.Role.values}
        self.role_links.exclude(role__in=wanted).delete()
        existing = {link.role for link in self.role_links.all()}
        UserRole.objects.bulk_create(
            [UserRole(user=self, role=role) for role in wanted - existing]
        )
        self._roles_cache = wanted

    def add_role(self, role):
        if role in self.Role.values:
            UserRole.objects.get_or_create(user=self, role=role)
            self.__dict__.pop('_roles_cache', None)

    @property
    def is_super_admin(self):
        return self.has_role(self.Role.SUPER_ADMIN)

    @property
    def is_manager(self):
        return self.has_role(self.Role.MANAGER)

    @property
    def is_teacher(self):
        return self.has_role(self.Role.TEACHER)

    @property
    def is_student(self):
        return self.has_role(self.Role.STUDENT)

    @property
    def teaches_only(self):
        """Викладає і при цьому не керує.

        Ролі додаються, тож `is_teacher` сам по собі нічого не каже про те, чи
        людина ще й менеджер. Скрізь, де інтерфейс звужується до «свого»
        (свій календар, свої предмети, свої групи), питати треба саме це —
        інакше керівник, який ще й викладає, втрачає керівницький бік.
        """
        return self.is_teacher and not self.can_manage_users

    # --- права --------------------------------------------------------

    @property
    def can_manage_users(self):
        """Add/remove users and change their access rights."""
        return self.is_super_admin or self.is_manager

    def can_assign_role(self, role):
        """Which roles this user is allowed to grant to somebody else."""
        if self.is_super_admin:
            return role in self.Role.values
        if self.is_manager:
            return role in (self.Role.TEACHER, self.Role.STUDENT)
        return False

    def can_edit_user(self, target):
        """Whether this user may edit/remove the target account at all.

        A manager may not touch an account that carries any role they cannot
        grant — so a colleague who both manages and teaches stays off-limits.
        """
        if self.is_super_admin:
            return True
        if self.is_manager:
            return bool(target.roles) and all(
                self.can_assign_role(role) for role in target.roles
            )
        return False

    @property
    def assignable_roles(self):
        return [(value, label) for value, label in self.Role.choices
                if self.can_assign_role(value)]


class UserRole(models.Model):
    """One role held by one user.

    A join table rather than a list in a column: the user list filters and
    sorts by role, and SQLite cannot index into a JSON array.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_links',
        verbose_name='Користувач',
    )
    role = models.CharField('Роль', max_length=20, choices=User.Role.choices)

    class Meta:
        verbose_name = 'Роль користувача'
        verbose_name_plural = 'Ролі користувачів'
        constraints = [
            models.UniqueConstraint(fields=['user', 'role'], name='unique_user_role'),
        ]

    def __str__(self):
        return f'{self.user} — {self.get_role_display()}'
