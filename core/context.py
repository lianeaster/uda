"""Контекст, потрібний на кожній сторінці.

Підвал із контактами рендериться і на публічному сайті, і на платформі, тож
дані для нього не можуть жити у в'юшках `core`.
"""

from center import content as center
from . import content


def site(request):
    return {
        'contacts': content.CONTACTS,
        'socials': content.SOCIALS,
        'site_description': content.DESCRIPTION,
        # Академія — підрозділ Центру, тож його назва потрібна і їй (смуга над шапкою).
        'center_name': center.NAME,
        'center_short_name': center.SHORT_NAME,
    }
