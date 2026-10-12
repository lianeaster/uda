"""Сховище статики для проду.

nginx віддає `/static/` з `expires 30d`, тож файл із незмінною назвою браузер
тримає місяць: після деплою людина бачить нову сторінку зі старими стилями й
скриптами. Тут `collectstatic` дописує до назви кожного файла хеш його вмісту
(`style.css` → `style.3f2a….css`), а `{% static %}` віддає саме таку адресу:
змінився файл — змінилась адреса, і кеш більше не заважає.
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class HashedStaticStorage(ManifestStaticFilesStorage):
    # Файл, якого немає в маніфесті, — це зламана картинка, а не привід
    # валити всю сторінку: віддаємо звичайну адресу без хеша.
    manifest_strict = False
