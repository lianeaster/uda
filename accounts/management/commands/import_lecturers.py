"""Створює облікові записи викладачів за списком лекторів публічного сайту."""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from core import content

from ...models import User


def username_for(lecturer):
    """Логін береться зі слага файлу фотографії.

    Це вже вивірена вручну транслітерація («Олександр Рябцев» →
    `olexandr-ryabtsev`), тож надійніше за автоматичну. Префікс `bc-` у
    файлі засновниці — назва теки оригіналу, до імені він стосунку не має.
    """
    slug = os.path.splitext(os.path.basename(lecturer['photo']))[0]
    return slug.removeprefix('bc-')


def split_name(full_name):
    """Список подано як «Ім'я Прізвище» — саме в такому порядку."""
    first, _, last = full_name.partition(' ')
    return first, last


class Command(BaseCommand):
    help = 'Додає лекторів публічного сайту (core.content.LECTURERS) як викладачів платформи.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показати, що буде зроблено, нічого не записуючи.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.quiet = options['verbosity'] == 0
        created, updated, skipped = [], [], []

        for lecturer in content.LECTURERS:
            username = username_for(lecturer)
            first_name, last_name = split_name(lecturer['name'])
            existing = User.objects.filter(username=username).first()

            if existing is None:
                if not dry_run:
                    user = User(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    # Пароль не вигадуємо: акаунт неактивний для входу, поки
                    # супер-адмін не задасть пароль у Django admin.
                    user.set_unusable_password()
                    user.save()
                    user.add_role(User.Role.TEACHER)
                created.append(f'{username} — {lecturer["name"]}')
                continue

            if not existing.is_teacher:
                roles = ', '.join(label for _, label in existing.role_labels) or 'без ролі'
                skipped.append(f'{username} — логін уже зайнятий, ролі: {roles}')
                continue

            changes = []
            if existing.first_name != first_name:
                changes.append(f"ім'я {existing.first_name or '—'} → {first_name}")
                existing.first_name = first_name
            if existing.last_name != last_name:
                changes.append(f'прізвище {existing.last_name or "—"} → {last_name}')
                existing.last_name = last_name
            if changes:
                if not dry_run:
                    existing.save(update_fields=['first_name', 'last_name'])
                updated.append(f'{username} — {", ".join(changes)}')

        self._report('Створено', created, self.style.SUCCESS)
        self._report('Оновлено', updated, self.style.WARNING)
        self._report('Пропущено', skipped, self.style.ERROR)

        if not self.quiet:
            total = User.objects.with_role(User.Role.TEACHER).count()
            prefix = '[--dry-run] ' if dry_run else ''
            self.stdout.write(
                f'\n{prefix}Лекторів у списку: {len(content.LECTURERS)}. '
                f'Викладачів на платформі: {total}.'
            )
            if created and not dry_run:
                self.stdout.write(
                    'Паролі не задано — новачки не зможуть увійти, поки супер-адмін '
                    'не встановить пароль у Django admin.'
                )
        if dry_run:
            transaction.set_rollback(True)

    def _report(self, title, rows, style):
        if not rows or self.quiet:
            return
        self.stdout.write(style(f'\n{title} ({len(rows)}):'))
        for row in rows:
            self.stdout.write(f'  {row}')
