"""Контекст, потрібний на кожній сторінці.

Підвал із контактами рендериться і на публічному сайті, і на платформі, тож
дані для нього не можуть жити у в'юшках `core`.
"""

from center import content as center
from center import pages as center_pages
from . import content


def site(request):
    return {
        'contacts': content.CONTACTS,
        'socials': content.SOCIALS,
        'site_description': content.DESCRIPTION,
        # Академія — підрозділ Центру, тож його назва потрібна і їй (смуга над шапкою).
        'center_name': center.NAME,
        'center_short_name': center.SHORT_NAME,
        # Академій дві; кожна посилається на сусідню.
        'food_academy_name': center.FOOD_ACADEMY_NAME,
        'platform_name': center.PLATFORM_NAME,
        # Розділи сайту Центру: шапка Центру й колонка Центру в спільному підвалі.
        'center_nav': center_pages.NAV,
        'center_footer_nav': center_pages.FOOTER_NAV,
        'center_tagline': center_pages.TAGLINE,
        'center_closing': center_pages.CLOSING,
    }
