"""Створює облікові записи викладачів за списком лекторів публічного сайту."""

import os

from django.core.management.base import BaseCommand
from django.db import transaction

from core import content

from ...models import User


def username_for(lecturer):
    """Логін-кандидат: слаг файлу фотографії.

    Це вже вивірена вручну транслітерація («Олександр Рябцев» →
    `olexandr-ryabtsev`), тож надійніше за автоматичну.
    """
    return os.path.splitext(os.path.basename(lecturer['photo']))[0]


def matching_accounts(lecturer):
    """Облікові записи, які можуть належати цьому лекторові.

    Спершу за логіном-слагом. Якщо такого немає — за ПІБ серед викладачів:
    та сама людина могла бути заведена вручну під робочим логіном (Катерина
    Камишева — `manager`), і тоді імпорт мусить її знайти, а не створити
    двійника під слагом. Кількох однофамільців не вибираємо навмання —
    повертаємо всіх, а команда про це скаже.
    """
    by_login = User.objects.filter(username=username_for(lecturer))
    if by_login.exists():
        return list(by_login)
    first_name, last_name = split_name(lecturer['name'])
    return list(User.objects.with_role(User.Role.TEACHER).filter(
        first_name=first_name, last_name=last_name))


def split_name(full_name):
    """Список подано як «Ім'я Прізвище» — саме в такому порядку."""
    first, _, last = full_name.partition(' ')
    return first, last


def is_the_lecturer(user, lecturer):
    """Чи належить знайдений під слагом запис саме цьому лекторові.

    Роль «Викладач» тут не вирішує: лектор публічного сайту може працювати на
    платформі керівницею й лишатися без цієї ролі — так у Ольги Бурканової,
    арт-директорки Академії. Тому питаємо інакше: збіглося ПІБ **або** людина
    таки викладає. Перше пускає керівницю, друге — викладачку, чиє прізвище
    змінилося з часу останнього імпорту; сторонню людину, яка просто зайняла
    логін, не пускає ні те, ні те.
    """
    first_name, last_name = split_name(lecturer['name'])
    same_name = (user.first_name, user.last_name) == (first_name, last_name)
    return same_name or user.is_teacher


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
            found = matching_accounts(lecturer)

            if len(found) > 1:
                logins = ', '.join(sorted(person.username for person in found))
                skipped.append(f'{username} — на це ПІБ кілька акаунтів ({logins}), '
                               f'зведіть їх: `manage.py merge_users`')
                continue
            existing = found[0] if found else None

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

            if not is_the_lecturer(existing, lecturer):
                roles = ', '.join(label for _, label in existing.role_labels) or 'без ролі'
                skipped.append(f'{username} — логін зайнятий іншою людиною '
                               f'({existing.display_name}, {roles})')
                continue

            # Зміни — те, що команда справді записує; примітки лише
            # пояснюють, що вона побачила. Змішувати їх не варто, інакше
            # «Оновлено» показує людей, яких ніхто не змінював.
            changes, notes = [], []
            if existing.username != username:
                notes.append(f'під логіном {existing.username}')
            if not existing.is_teacher:
                # Ролей наявному записові не додаємо: як розподілені ролі —
                # рішення керівництва, а не списку лекторів на сайті.
                roles = ', '.join(label for _, label in existing.role_labels) or 'без ролі'
                notes.append(f'ролі лишаємо як є: {roles}')
            if existing.first_name != first_name:
                changes.append(f"ім'я {existing.first_name or '—'} → {first_name}")
                existing.first_name = first_name
            if existing.last_name != last_name:
                changes.append(f'прізвище {existing.last_name or "—"} → {last_name}')
                existing.last_name = last_name

            if changes:
                if not dry_run:
                    existing.save(update_fields=['first_name', 'last_name'])
                updated.append(f'{username} — {", ".join(changes + notes)}')
            else:
                skipped.append(f'{username} — уже є' + (
                    f' ({", ".join(notes)})' if notes else ''))

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
