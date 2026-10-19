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
