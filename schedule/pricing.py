"""Вартість навчання: години програми × ставка викладача + комісія Академії.

Три різні цифри, які легко сплутати:

- **вартість** — базовий сценарій: година викладача + 20% Академії
  (`BASE_COMMISSION`). Скільки Академія має зібрати за предмет, модуль чи курс;
- **індивідуальна ціна** — година викладача + 30% (`INDIVIDUAL_COMMISSION`):
  кожну зустріч узгоджують окремо, а ділити ці витрати нема з ким;
- **ціна для людини в групі** — її Академія ставить окремо, у євро
  (`Course.group_price_eur`); вартість ділиться між студентами групи.

Комісія покриває адміністрування, податки й банк. Екскурсія є лише в
«Майстрі» (`Course.excursion_price`): у групову ціну вона входить, в
індивідуальну — ні.

Суми бачать лише менеджер і супер-адмін (`user.can_manage_users`); решта —
години без грошей. Тому в'юшки рахують вартість тільки для них.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

STANDARD_RATE = 1000         # грн за годину, якщо в картці викладача не вказано іншої
BASE_COMMISSION = 20         # комісія Академії в базовому сценарії, %
INDIVIDUAL_COMMISSION = 30   # комісія з індивідуального навчання, %


def teacher_rate(user):
    return user.hourly_rate or STANDARD_RATE


def lecturers_rate(lecturers):
    """Ставка години для тих, хто веде.

    Одночасно заняття веде одна людина. Коли їх кілька (чергуються), беремо
    найвищу ставку — щоб вартість не вийшла заниженою.
    """
    return max((teacher_rate(t) for t in lecturers), default=STANDARD_RATE)


def subject_rate(subject):
    """Ставка предмета за його каталогом викладачів (поза конкретним курсом)."""
    return lecturers_rate(subject.teachers.all())


def _whole(amount):
    return int(Decimal(amount).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Cost:
    hours: Decimal = Decimal(0)
    teachers: int = 0        # викладачам, грн
    rate: int | None = None  # ставка години; у сумі кількох предметів її немає

    @property
    def academy(self):
        """Комісія Академії в базовому сценарії."""
        return _whole(self.teachers * BASE_COMMISSION / 100)

    @property
    def price(self):
        """Вартість: викладачам + 20% Академії."""
        return self.teachers + self.academy

    @property
    def individual(self):
        """Скільки платить індивідуальний студент: викладачам + 30%."""
        return self.teachers + _whole(self.teachers * INDIVIDUAL_COMMISSION / 100)

    def __add__(self, other):
        return Cost(self.hours + other.hours, self.teachers + other.teachers)


def link_cost(link):
    """Вартість предмета в програмі курсу (`CourseSubject`); None — годин немає."""
    if link.hours is None:
        return None
    rate = lecturers_rate(link.lecturers)
    teachers = _whole(link.hours * rate)
    return Cost(link.hours, teachers, rate)


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

    - вартість для Академії — викладачам за всі години + 20%;
    - студент загальної групи — групова ціна в євро (з екскурсією, якщо вона є);
    - Early Bird — групова мінус вартість екскурсії; без екскурсії — немає;
    - індивідуальний студент — викладачам + 30%, екскурсія окремо.
    Групової ціни не вказано — групових пропозицій немає (None).
    """
    group = early_bird = None
    if course.group_price_eur:
        group = from_eur(course.group_price_eur, rate)
        if course.excursion_price and group.uah is not None:
            early_bird = from_uah(group.uah - course.excursion_price, rate)
    return {
        'academy': from_uah(total.price, rate),
        'group': group,
        'early_bird': early_bird,
        'individual': from_uah(total.individual, rate),
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
    за id з матриці, курс НБУ й групові ціни готових курсів (`Course.code`). Оплата викладачам і
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
            subjects[key] = {'hours': float(cost.hours), 'uah': cost.individual}

    # Групові ціни готових курсів — за кодом курсу в матриці.
    courses = {}
    for other in Course.objects.exclude(code='').exclude(group_price_eur=None):
        group = from_eur(other.group_price_eur, rate)
        offer = {'eur': group.eur, 'uah': group.uah, 'earlyBird': None}
        if other.excursion_price and group.uah is not None:
            offer['earlyBird'] = from_uah(group.uah - other.excursion_price, rate).__dict__
        courses[other.code] = offer
    return {
        'rate': float(rate) if rate else None,
        'rateDate': f'{euro.date:%d.%m.%Y}' if euro else None,
        'excursion': course.excursion_price,
        'subjects': subjects,
        'courses': courses,
    }
