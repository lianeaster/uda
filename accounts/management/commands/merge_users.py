"""Зводить два облікові записи однієї людини в один.

Дублікати трапляються природно: та сама людина заведена вручну під робочим
логіном і ще раз — імпортом зі списку лекторів, уже під іншим прізвищем.
Команда переносить усе, що встигло наростити зайвий запис, і видаляє його.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from schedule.models import Enrollment, GroupSubject, ScheduleEntry

from ...models import User

# Поля картки: заповнене в тому, кого зводимо, переїжджає лише в порожнє.
# Ім'я й прізвище тут навмисно немає — виживає те, під яким людину знають.
CARD_FIELDS = ['patronymic', 'photo', 'about', 'education', 'interests', 'experience', 'email']


class Command(BaseCommand):
    help = ('Зводить облікові записи однієї людини: merge_users <логін, що лишається> '
            '<логін-дублікат> [ще дублікати…]')

    def add_arguments(self, parser):
        parser.add_argument('keep', help='Логін, який лишається.')
        parser.add_argument('merge', nargs='+', help='Логіни-дублікати — їх буде видалено.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Показати, що буде зроблено, нічого не змінюючи.')

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.quiet = options['verbosity'] == 0
        keeper = self.get_user(options['keep'])

        for username in options['merge']:
            duplicate = self.get_user(username)
            if duplicate.pk == keeper.pk:
                raise CommandError('Той самий обліковий запис і лишається, і зводиться.')
            self.merge(keeper, duplicate, dry_run)

        if dry_run:
            transaction.set_rollback(True)

    def get_user(self, username):
        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError(f'Облікового запису «{username}» немає.')
        return user

    def merge(self, keeper, duplicate, dry_run):
        moved = []

        # 1. Роботу переносимо всю: предмети, заняття в групах, навчання,
        #    записи розкладу — і ті, що людина створила, і ті, що розглянула.
        moved += self.move_links(keeper, duplicate, dry_run)

        # 2. Ролі додаються, а не заміщаються: якщо дублікат був викладачем,
        #    а той, хто лишається, — менеджером, людина є і тим, і тим.
        new_roles = duplicate.roles - keeper.roles
        if new_roles:
            labels = dict(User.Role.choices)
            moved.append('ролі: ' + ', '.join(labels[role] for role in sorted(new_roles)))
            if not dry_run:
                keeper.set_roles(keeper.roles | duplicate.roles)

        # 3. Картка: беремо лише те, чого в тому, хто лишається, немає.
        for name in CARD_FIELDS:
            theirs = getattr(duplicate, name)
            if theirs and not getattr(keeper, name):
                moved.append(f'{keeper._meta.get_field(name).verbose_name.lower()} — з картки дубліката')
                if not dry_run:
                    setattr(keeper, name, theirs)
        if not dry_run:
            keeper.save()
            # Фото не чіпаємо у storage: файл лишається на місці, змінюється
            # тільки те, чия картка на нього вказує.
            duplicate.delete()

        if not self.quiet:
            prefix = '[--dry-run] ' if dry_run else ''
            self.stdout.write(self.style.SUCCESS(
                f'\n{prefix}«{duplicate.username}» → «{keeper.username}» ({keeper.display_name})'))
            for row in moved or ['переносити нічого — дублікат був порожній']:
                self.stdout.write(f'  {row}')

    def move_links(self, keeper, duplicate, dry_run):
        moved = []

        subjects = list(duplicate.subjects.all())
        if subjects:
            moved.append(f'предметів у каталозі: {len(subjects)}')
            if not dry_run:
                keeper.subjects.add(*subjects)
                duplicate.subjects.clear()

        for queryset, field, label in [
            (GroupSubject.objects.filter(teacher=duplicate), 'teacher', 'предметів у групах'),
            (ScheduleEntry.objects.filter(created_by=duplicate), 'created_by', 'створених записів розкладу'),
            (ScheduleEntry.objects.filter(reviewed_by=duplicate), 'reviewed_by', 'розглянутих пропозицій'),
        ]:
            count = queryset.count()
            if count:
                moved.append(f'{label}: {count}')
                if not dry_run:
                    queryset.update(**{field: keeper})

        # Навчання в групі унікальне за (група, студент, початок), тож запис,
        # який зіткнувся б із наявним, не переносимо, а прибираємо разом із
        # дублікатом: це та сама подія, записана двічі.
        enrollments = Enrollment.objects.filter(student=duplicate)
        clashing = [
            e.pk for e in enrollments
            if Enrollment.objects.filter(
                group=e.group, student=keeper, start_date=e.start_date).exists()
        ]
        movable = enrollments.exclude(pk__in=clashing)
        if movable.exists():
            moved.append(f'навчання в групах: {movable.count()}')
            if not dry_run:
                movable.update(student=keeper)
        if clashing:
            moved.append(f'повторних записів про навчання прибрано: {len(clashing)}')
            if not dry_run:
                Enrollment.objects.filter(pk__in=clashing).delete()

        return moved
