"""Контекст, потрібний на кожній сторінці.

Підвал із контактами рендериться і на публічному сайті, і на платформі, тож
дані для нього не можуть жити у в'юшках `core`.
"""

from . import content


def site(request):
    return {
        'contacts': content.CONTACTS,
        'socials': content.SOCIALS,
        'site_description': content.DESCRIPTION,
    }
