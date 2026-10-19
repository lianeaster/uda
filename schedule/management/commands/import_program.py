"""Заносить програму курсу (див. `schedule.programs`): модулі, предмети з
годинами та їхніх викладачів зі ставками.

Номер і місце предмета команда звіряє з графіком щоразу. Години, модуль,
екскурсію й ставку — лише там, де порожньо: їх правлять на платформі, і
повторний імпорт не має затирати правки менеджерів."""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User

from ... import programs
from ...models import Course, CourseSubject, Module, Subject


class Command(BaseCommand):
    help = 'Створює предмети курсу «Майстер дистиляції» з графіка і призначає викладачів.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показати, що буде зроблено, нічого не записуючи.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.quiet = options['verbosity'] == 0
        self.created_teachers, self.blocked = [], []
        created, updated, assigned = [], [], []
        teaching = set()

        course, made = Course.objects.get_or_create(name=programs.COURSE)
        if made:
            self.created_teachers.append(f'курс «{course.name}»')
        if course.excursion_price is None:
            course.excursion_price = programs.EXCURSION_PRICE
            course.save(update_fields=['excursion_price'])

        modules = {}
        for position, code, name, module_format in programs.modules():
            modules[code], _ = Module.objects.update_or_create(
                course=course, name=name,
                defaults={'code': code, 'format': module_format, 'position': position})

        seen = set()
        for position, code, name, module_code, lecturer_labels, hours in programs.subjects():
            subject, is_new = Subject.objects.get_or_create(name=name)
            seen.add(subject.pk)
            link = CourseSubject.objects.filter(course=course, subject=subject).first()
            module = modules[module_code]

            if is_new or link is None:
                if not self.dry_run:
                    CourseSubject.objects.create(
                        course=course, subject=subject, code=code, position=position,
                        module=module, hours=hours)
                created.append(f'{code} {name}' + ('' if is_new else ' — додано в програму курсу'))
            else:
                changes = [field for field, value in (('code', code), ('position', position))
                           if getattr(link, field) != value]
                for field, value in (('module', module), ('hours', hours)):
                    if getattr(link, field) is None and value is not None:
                        changes.append(field)
                link.code, link.position = code, position
                link.module = link.module or module
                link.hours = hours if link.hours is None else link.hours
                if changes:
                    if not self.dry_run:
                        link.save(update_fields=changes)
                    updated.append(f'{code} {name} — {", ".join(changes)}')

            teachers = [t for t in (self._resolve(label) for label in lecturer_labels) if t]
            teaching.update(t.pk for t in teachers)
            if teachers and not self.dry_run:
                subject.teachers.set(teachers)
            if teachers:
                assigned.append(
                    f'{code} {name} → {", ".join(t.get_full_name() or t.username for t in teachers)}'
                )

        self._report('Створено предметів', created, self.style.SUCCESS)
        self._report('Оновлено предметів', updated, self.style.WARNING)
        self._report('Створено викладачів', self.created_teachers, self.style.SUCCESS)
        self._report('Призначено', assigned, self.style.SUCCESS)
        self._report('Не призначено', self.blocked, self.style.ERROR)

        stray = course.program.exclude(subject_id__in=seen).select_related('subject')
        if stray:
            self._report(
                'Предмети курсу поза програмою (не чіпав)',
                [link.subject.name for link in stray],
                self.style.WARNING,
            )

        if not self.quiet:
            prefix = '[--dry-run] ' if self.dry_run else ''
            self.stdout.write(
                f'\n{prefix}Предметів у програмі: {len(seen)}. '
                f'Викладачів задіяно: {len(teaching)}.'
            )
        if self.dry_run:
            transaction.set_rollback(True)

    def _resolve(self, label):
        """Підпис із графіка -> обліковий запис викладача, або None."""
        username, first_name, last_name = programs.LECTURERS[label]
        user = User.objects.filter(username=username).first()
        rate = programs.RATES.get(username)

        if user is not None and rate and user.hourly_rate is None and not self.dry_run:
            user.hourly_rate = rate
            user.save(update_fields=['hourly_rate'])

        if user is None:
            if self.dry_run:
                self.created_teachers.append(f'{username} — {first_name} {last_name}'.strip())
                return None
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                hourly_rate=rate,
            )
            # Той самий принцип, що й в `import_lecturers`: паролів не вигадуємо.
            user.set_unusable_password()
            user.save()
            user.add_role(User.Role.TEACHER)
            self.created_teachers.append(f'{username} — {user.get_full_name()}')
            return user

        if not user.is_teacher:
            roles = ', '.join(lbl for _, lbl in user.role_labels) or 'без ролі'
            note = f'«{label}» → {username} не має ролі викладача (зараз: {roles})'
            if note not in self.blocked:
                self.blocked.append(note)
            return None
        return user

    def _report(self, title, rows, style):
        if not rows or self.quiet:
            return
        self.stdout.write(style(f'\n{title} ({len(rows)}):'))
        for row in rows:
            self.stdout.write(f'  {row}')
