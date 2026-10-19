"""Вартість навчання: години програми × ставка викладача + комісія Академії.

Дві різні цифри, які легко сплутати:

- **вартість** — скільки Академія має зібрати за предмет, модуль чи курс:
  оплата викладачам + комісія. Індивідуальний студент платить її сам;
- **ціна для людини в групі** — та сама вартість, поділена між студентами.
  Тут її немає: групову ціну Академія ставить окремо.

Комісія покриває адміністрування, податки й банк. Для індивідуального курсу
її піднято з 20% до 30%: кожну зустріч узгоджують окремо, а ділити ці
витрати нема з ким. Екскурсія у вартість не входить — `Course.excursion_price`.

Суми бачать лише менеджер і супер-адмін (`user.can_manage_users`); решта —
години без грошей. Тому в'юшки рахують вартість тільки для них.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

STANDARD_RATE = 1000       # грн за годину, якщо в картці викладача не вказано іншої
COMMISSION_PERCENT = 30    # комісія Академії з індивідуального навчання


def teacher_rate(user):
    return user.hourly_rate or STANDARD_RATE


def subject_rate(subject):
    """Ставка години предмета.

    Одночасно заняття веде одна людина. Коли предмет можуть вести кілька
    викладачів, беремо найвищу ставку — щоб вартість не вийшла заниженою.
    """
    rates = [teacher_rate(t) for t in subject.teachers.all()]
    return max(rates, default=STANDARD_RATE)


def _whole(amount):
    return int(Decimal(amount).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Cost:
    hours: Decimal = Decimal(0)
    teachers: int = 0      # викладачам, грн
    academy: int = 0       # комісія Академії, грн
    rate: int | None = None  # ставка години; у сумі кількох предметів її немає

    @property
    def price(self):
        """Скільки платить індивідуальний студент."""
        return self.teachers + self.academy

    def __add__(self, other):
        return Cost(self.hours + other.hours, self.teachers + other.teachers,
                    self.academy + other.academy)


def link_cost(link):
    """Вартість предмета в програмі курсу (`CourseSubject`); None — годин немає."""
    if link.hours is None:
        return None
    rate = subject_rate(link.subject)
    teachers = _whole(link.hours * rate)
    return Cost(link.hours, teachers, _whole(teachers * COMMISSION_PERCENT / 100), rate)


def program_cost(links):
    """Разом по рядках програми: [(рядок, вартість)], сума.

    Рядки без годин у суму не входять — вони лишаються в таблиці з прочерком.
    """
    rows = [(link, link_cost(link)) for link in links]
    total = sum((cost for _, cost in rows if cost), Cost())
    return rows, total


# --- гривні й євро -----------------------------------------------------

@dataclass(frozen=True)
class Money:
    """Сума в гривнях і її еквівалент в євро за курсом НБУ (None — курсу немає)."""
    uah: int | None
    eur: int | None


def from_uah(uah, rate):
    return Money(uah, _whole(uah / rate) if rate else None)


def from_eur(eur, rate):
    return Money(_whole(eur * rate) if rate else None, eur)


def course_offers(course, total, rate):
    """Чотири ціни курсу для картки, у гривнях і євро на сьогодні.

    - для Академії — скільки вона платить викладачам за всі години;
    - студент загальної групи — групова ціна в євро (разом з екскурсією);
    - Early Bird — групова мінус вартість екскурсії;
    - індивідуальний студент — години × ставки + комісія, екскурсія окремо.
    Групової ціни не вказано — групових пропозицій немає (None).
    """
    group = early_bird = None
    if course.group_price_eur:
        group = from_eur(course.group_price_eur, rate)
        if course.excursion_price and group.uah is not None:
            early_bird = from_uah(group.uah - course.excursion_price, rate)
    return {
        'academy': from_uah(total.teachers, rate),
        'group': group,
        'early_bird': early_bird,
        'individual': from_uah(total.price, rate),
    }


# --- публічний конструктор курсів ---------------------------------------

# Номери предметів у матриці компетенцій (static/js/competency-data.js)
# виправлені там, де графік повторюється («8.2» двічі, «10.7» двічі);
# решта збігається з номером у програмі «Майстра».
MATRIX_IDS = {
    'Альтернативна витримка': '8.1',
    'Витримка в бочці': '8.2',
    'Авторське право': '10.7a',
    'Дистрибуція': '10.7b',
}


def public_prices():
    """Ціни для конструктора курсів на сайті Академії — лише те, що платить студент.

    Модуль конструктора — компетентність матриці, і її ціна — сума предметів
    «Майстра», з яких вона складається. Тож сюди йде ціна кожного предмета
    за id з матриці, курс НБУ й ціни готового «Майстра». Оплата викладачам і
    комісія окремо сюди не потрапляють. Курсу на платформі немає — None.
    """
    from . import exchange, programs
    from .models import Course

    course = Course.objects.filter(name=programs.COURSE).first()
    if course is None:
        return None
    euro = exchange.today_rate()
    rate = euro.rate if euro else None

    subjects = {}
    for link in course.ordered_program:
        cost = link_cost(link)
        if cost is not None and cost.hours:
            key = MATRIX_IDS.get(link.subject.name, link.code)
            subjects[key] = {'hours': float(cost.hours), 'uah': cost.price}

    master = None
    if course.group_price_eur:
        group = from_eur(course.group_price_eur, rate)
        master = {'eur': group.eur, 'uah': group.uah, 'earlyBird': None}
        if course.excursion_price and group.uah is not None:
            master['earlyBird'] = from_uah(group.uah - course.excursion_price, rate).__dict__
    return {
        'rate': float(rate) if rate else None,
        'rateDate': f'{euro.date:%d.%m.%Y}' if euro else None,
        'excursion': course.excursion_price,
        'subjects': subjects,
        'courses': {'master': master} if master else {},
    }
