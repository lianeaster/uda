"""Виплати викладачам: дні виплат, періоди й відомість з розкладу.

Академія платить двічі на місяць:

- **15-го** — за заняття з 1-го по 15-те;
- **30-го** — за заняття з 16-го до кінця місяця. У лютому, де 30-го немає,
  — в останній день місяця.

Відомість не зберігається — вона щоразу рахується з розкладу: прийняті
записи періоду × ставка того, хто веде (`schedule.pricing.teacher_rate`).
Поправили розклад — змінилась і відомість, зокрема вже минулого періоду.
"""

import calendar
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.urls import reverse

from schedule.models import ScheduleEntry
from schedule.pricing import teacher_rate

FIRST_PAYDAY = 15
SECOND_PAYDAY = 30
REMIND_DAYS_BEFORE = 3   # за скільки днів до виплати задача починає «горіти»


# --- дні виплат --------------------------------------------------------

def _second_payday(year, month):
    return dt.date(year, month, min(SECOND_PAYDAY, calendar.monthrange(year, month)[1]))


def _shift_month(day, delta):
    month = day.month - 1 + delta
    return dt.date(day.year + month // 12, month % 12 + 1, 1)


def payday_for(lesson_date):
    """День, у який платять за заняття цієї дати."""
    if lesson_date.day <= FIRST_PAYDAY:
        return lesson_date.replace(day=FIRST_PAYDAY)
    return _second_payday(lesson_date.year, lesson_date.month)


def is_payday(day):
    return payday_for(day) == day


def period(payday):
    """Перший і останній день занять, за які платять цього дня."""
    if payday.day == FIRST_PAYDAY:
        return payday.replace(day=1), payday
    last = calendar.monthrange(payday.year, payday.month)[1]
    return payday.replace(day=FIRST_PAYDAY + 1), payday.replace(day=last)


def next_payday(on=None):
    """Найближчий день виплати — сьогодні або пізніше."""
    on = on or dt.date.today()
    payday = payday_for(on)
    if payday >= on:
        return payday
    # 31-ше: за нього платили 30-го, наступна виплата — 15-го.
    return _shift_month(on, 1).replace(day=FIRST_PAYDAY)


def previous_payday(payday):
    if payday.day == FIRST_PAYDAY:
        before = _shift_month(payday, -1)
        return _second_payday(before.year, before.month)
    return payday.replace(day=FIRST_PAYDAY)


def following_payday(payday):
    if payday.day == FIRST_PAYDAY:
        return _second_payday(payday.year, payday.month)
    return _shift_month(payday, 1).replace(day=FIRST_PAYDAY)


# --- відомість ---------------------------------------------------------

def _whole(amount):
    return int(Decimal(amount).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def lesson_hours(entry):
    minutes = (entry.end_time.hour * 60 + entry.end_time.minute
               - entry.start_time.hour * 60 - entry.start_time.minute)
    return (Decimal(minutes) / 60).quantize(Decimal('0.01'))


@dataclass
class Lesson:
    entry: ScheduleEntry
    hours: Decimal
    amount: int


@dataclass
class TeacherPay:
    teacher: object
    rate: int
    lessons: list = field(default_factory=list)

    @property
    def hours(self):
        return sum((lesson.hours for lesson in self.lessons), Decimal(0))

    @property
    def amount(self):
        # Сума рядків, а не години × ставка: так відомість сходиться з
        # розшифровкою копійка в копійку, навіть коли заняття не в цілих годинах.
        return sum(lesson.amount for lesson in self.lessons)


@dataclass
class Statement:
    payday: dt.date
    start: dt.date
    end: dt.date
    teachers: list
    # Що в періоді є, але до виплати не потрапило — щоб менеджер бачив чому.
    without_teacher: list
    pending: list

    @property
    def hours(self):
        return sum((pay.hours for pay in self.teachers), Decimal(0))

    @property
    def amount(self):
        return sum(pay.amount for pay in self.teachers)

    @property
    def lesson_count(self):
        return sum(len(pay.lessons) for pay in self.teachers)


def _period_entries(start, end):
    return ScheduleEntry.objects.filter(date__range=(start, end)).select_related(
        'group__course', 'group_subject__subject', 'group_subject__teacher', 'created_by',
    ).order_by('date', 'start_time')


def statement(payday):
    """Кому й скільки платити цього дня — за прийнятими заняттями періоду.

    - Пропозиції на розгляді ще не заняття: вони не в сумі, а окремим списком.
    - Відхилені — не заняття взагалі.
    - День, заброньований під курс без предмета, не має викладача — платити
      нікому; такі дні теж окремим списком, щоб їх не загубили.
    """
    start, end = period(payday)
    by_teacher = {}
    without_teacher, pending = [], []
    for entry in _period_entries(start, end):
        if entry.status == ScheduleEntry.Status.PROPOSED:
            pending.append(entry)
            continue
        if entry.status != ScheduleEntry.Status.ACCEPTED:
            continue
        teacher = entry.teacher
        if teacher is None:
            without_teacher.append(entry)
            continue
        pay = by_teacher.get(teacher.pk)
        if pay is None:
            pay = by_teacher[teacher.pk] = TeacherPay(teacher, teacher_rate(teacher))
        hours = lesson_hours(entry)
        pay.lessons.append(Lesson(entry, hours, _whole(hours * pay.rate)))
    teachers = sorted(by_teacher.values(), key=lambda pay: pay.teacher.display_name)
    return Statement(payday, start, end, teachers, without_teacher, pending)


# --- нагадування -------------------------------------------------------

def _paid_lessons():
    """Записи, за які комусь платять: прийняті й з викладачем."""
    return ScheduleEntry.objects.filter(status=ScheduleEntry.Status.ACCEPTED).filter(
        Q(group_subject__isnull=False) | Q(source=ScheduleEntry.Source.TEACHER))


def payday_task_key(payday):
    return f'payday:{payday.isoformat()}'


def sync_payday_tasks(on=None):
    """Ставить спільну задачу керування на кожну виплату, за яку є заняття.

    Від попередньої виплати й далі: та, що вже минула, могла лишитися
    непроведеною. Задача, яка вже є, не чіпається — ні дата, ні те, що її
    виконали. Викликається там, де менеджер дивиться на задачі (кабінет,
    «Мої задачі», відомість), тож заняття, щойно додане в розклад, одразу
    дає нагадування.
    """
    from tasks.models import Task

    on = on or dt.date.today()
    since = period(previous_payday(next_payday(on)))[0]
    paydays = {payday_for(day) for day in
               _paid_lessons().filter(date__gte=since).dates('date', 'day')}
    if not paydays:
        return
    existing = set(Task.objects.filter(
        key__in=[payday_task_key(p) for p in paydays]).values_list('key', flat=True))
    missing = []
    for payday in sorted(paydays):
        key = payday_task_key(payday)
        if key in existing:
            continue
        start, end = period(payday)
        missing.append(Task(
            key=key,
            title=f'Виплата викладачам {payday:%d.%m.%Y}',
            notes=f'За заняття {start:%d.%m}–{end:%d.%m.%Y}. '
                  'Звірте відомість і проведіть виплату.',
            due_date=payday,
            remind_on=payday - dt.timedelta(days=REMIND_DAYS_BEFORE),
            link=f"{reverse('accounting:payroll')}?payday={payday.isoformat()}",
        ))
    # Дві вкладки відкрили кабінет одночасно — друга просто нічого не додасть.
    Task.objects.bulk_create(missing, ignore_conflicts=True)
