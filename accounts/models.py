from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a role that drives access across the whole platform."""

    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Супер-адмін'
        MANAGER = 'manager', 'Менеджер'
        TEACHER = 'teacher', 'Викладач'
        STUDENT = 'student', 'Студент'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name='Роль',
    )

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

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def can_manage_users(self):
        """Add/remove users and change their access rights."""
        return self.role in (self.Role.SUPER_ADMIN, self.Role.MANAGER)

    def can_assign_role(self, role):
        """Which roles this user is allowed to grant to somebody else."""
        if self.role == self.Role.SUPER_ADMIN:
            return role in self.Role.values
        if self.role == self.Role.MANAGER:
            return role in (self.Role.TEACHER, self.Role.STUDENT)
        return False

    def can_edit_user(self, target):
        """Whether this user may edit/remove the target account at all."""
        if self.role == self.Role.SUPER_ADMIN:
            return True
        if self.role == self.Role.MANAGER:
            return target.role in (self.Role.TEACHER, self.Role.STUDENT)
        return False

    @property
    def assignable_roles(self):
        return [(value, label) for value, label in self.Role.choices if self.can_assign_role(value)]
