"""Офіційний курс євро НБУ на сьогодні.

Курс за день питаємо в НБУ один раз і зберігаємо (`EuroRate`). Якщо НБУ не
відповідає, беремо останній збережений — сторінка не падає й не чекає, а
дата поруч із курсом показує, що він не сьогоднішній.
"""

import json
import logging
from decimal import Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import EuroRate

log = logging.getLogger(__name__)

NBU_URL = ('https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange'
           '?valcode=EUR&date={day:%Y%m%d}&json')
TIMEOUT = 3   # секунди: краще вчорашній курс, ніж сторінка, що висить
# НБУ не відповів — годину не питаємо знову: курс стоїть і на публічних
# сторінках, і кожен відвідувач чекав би ці секунди.
RETRY_AFTER = 60 * 60
FAILED_KEY = 'nbu-euro-failed'


def fetch(day):
    """Курс НБУ на день, ₴ за 1 €."""
    if not settings.NBU_RATES_ONLINE:
        raise URLError('мережу вимкнено (NBU_RATES_ONLINE)')
    request = Request(NBU_URL.format(day=day), headers={'User-Agent': 'uda-platform'})
    with urlopen(request, timeout=TIMEOUT) as response:
        data = json.load(response)
    return Decimal(str(data[0]['rate']))


def today_rate():
    """`EuroRate` на сьогодні, або останній відомий, або None — якщо курсу ще не було."""
    today = timezone.localdate()
    stored = EuroRate.objects.filter(date=today).first()
    if stored is not None:
        return stored
    if cache.get(FAILED_KEY):
        return EuroRate.objects.first()
    try:
        rate = fetch(today)
    except (URLError, OSError, ValueError, KeyError, IndexError) as error:
        log.warning('Курс НБУ на %s недоступний: %s', today, error)
        cache.set(FAILED_KEY, True, RETRY_AFTER)
        return EuroRate.objects.first()
    stored, _ = EuroRate.objects.get_or_create(date=today, defaults={'rate': rate})
    return stored
