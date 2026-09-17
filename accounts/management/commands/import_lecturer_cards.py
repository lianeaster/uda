"""Стягує фото й біографії лекторів зі старого сайту Академії в їхні картки.

Фото людини — медіа, а не статика: далі його змінює сама людина у своїй
картці. Тому файли йдуть у `MEDIA_ROOT/profiles/`, а не в `static/`.
"""

import os
from io import BytesIO
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from core import content

from ...models import User
from .import_lecturers import is_the_lecturer, matching_accounts, username_for

# Оригінали (не обрізані під сітку сайту) лежать поруч зі стилізованими
# копіями — беремо їх. Розширення в джерелі різні, тож пробуємо обидва.
SITE_PHOTOS = 'https://distillingacademy.com.ua/sites/default/files/field/image/lecturer/'
EXTENSIONS = ['.jpg', '.png']
TIMEOUT = 20


def download(url):
    """Байти зображення або None, якщо сайт не віддав саме зображення.

    Drupal на невідомий файл відповідає сторінкою 404, а не помилкою, тож
    просто перевіряємо, що прийшла картинка, — інакше в картку лягла б
    розмітка з розширенням .jpg.
    """
    request = Request(url, headers={'User-Agent': 'UDA-platform/import-lecturer-cards'})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            data = response.read()
    except (URLError, OSError):
        return None
    return data if is_image(data) else None


def is_image(data):
    try:
        Image.open(BytesIO(data)).verify()
    except (UnidentifiedImageError, OSError):
        return False
    return True


def from_site(slug):
    for extension in EXTENSIONS:
        data = download(f'{SITE_PHOTOS}{slug}{extension}')
        if data:
            return extension, data
    return None, None


def from_static(lecturer):
    """Копія того самого фото, збережена для публічного сайту.

    Резерв на випадок, коли сайт недоступний. Беремо саме `source/` —
    недоторкані оригінали: у теці вище лежать портрети, вже зведені під
    сторінку лекторів (`manage.py normalize_portraits`), і карточка на
    платформі не мусить залежати від того, чи їх уже перерахували.
    """
    name = os.path.basename(lecturer['photo'])
    path = settings.BASE_DIR / 'static' / 'img' / 'lecturers' / 'source' / name
    if not path.exists():
        return None, None
    return path.suffix, path.read_bytes()


class Command(BaseCommand):
    help = ('Стягує фото лекторів зі distillingacademy.com.ua у картки «Про мене» '
            'і заповнює порожнє поле «Про мене» їхньою біографією з сайту.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Показати, що буде зроблено, нічого не записуючи.')
        parser.add_argument('--replace', action='store_true',
                            help='Перезаписати фото й текст там, де вони вже є.')
        parser.add_argument('--local', action='store_true',
                            help='Брати фото з static/img/lecturers, не звертаючись до сайту.')

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        replace = options['replace']
        local = options['local']
        self.quiet = options['verbosity'] == 0
        done, skipped, failed = [], [], []
        with_photo = 0

        for lecturer in content.LECTURERS:
            username = username_for(lecturer)
            # Логін може й не збігатися зі слагом — людину шукаємо так само,
            # як `import_lecturers`, інакше фото пішло б у порожню картку
            # новоствореного двійника.
            found = matching_accounts(lecturer)
            if len(found) > 1:
                logins = ', '.join(sorted(person.username for person in found))
                skipped.append(f'{username} — на це ПІБ кілька акаунтів ({logins})')
                continue
            teacher = found[0] if found else None
            if teacher is None:
                skipped.append(f'{username} — акаунта немає, спершу `import_lecturers`')
                continue
            if not is_the_lecturer(teacher, lecturer):
                skipped.append(f'{username} — логін зайнятий іншою людиною '
                               f'({teacher.display_name})')
                continue

            wants_photo = replace or not teacher.photo
            wants_about = replace or not teacher.about
            if teacher.photo:
                with_photo += 1
            if not (wants_photo or wants_about):
                skipped.append(f'{username} — картка вже заповнена')
                continue

            changes = []
            extension = data = None
            if wants_photo:
                slug = os.path.splitext(os.path.basename(lecturer['photo']))[0]
                extension, data = (from_static(lecturer) if local else from_site(slug))
                if data is None and not local:
                    # Сайт міг і не відповісти — тоді беремо збережену копію.
                    extension, data = from_static(lecturer)
                    if data is not None:
                        changes.append('фото з локальної копії (сайт не відповів)')
                if data is None:
                    failed.append(f'{username} — фото не вдалося дістати')
                    continue
                if not changes:
                    changes.append('фото з локальної копії' if local else 'фото з сайту')

            if wants_about:
                changes.append('текст «Про мене»')

            if not dry_run:
                if wants_photo:
                    # Storage не перезаписує файли, а додає суфікс, тож старий
                    # знімок прибираємо самі.
                    teacher.photo.delete(save=False)
                    teacher.photo.save(
                        f'{teacher.username}{extension}', ContentFile(data), save=False)
                if wants_about:
                    teacher.about = lecturer['bio']
                teacher.save(update_fields=['photo', 'about'])
            if wants_photo and not replace:
                with_photo += 1
            done.append(f'{username} — {", ".join(changes)}')

        self._report('Оновлено', done, self.style.SUCCESS)
        self._report('Пропущено', skipped, self.style.WARNING)
        self._report('Не вдалося', failed, self.style.ERROR)

        if not self.quiet:
            prefix = '[--dry-run] ' if dry_run else ''
            self.stdout.write(
                f'\n{prefix}Фото в картках лекторів: {with_photo} з {len(content.LECTURERS)}.')
        if dry_run:
            transaction.set_rollback(True)

    def _report(self, title, rows, style):
        if not rows or self.quiet:
            return
        self.stdout.write(style(f'\n{title} ({len(rows)}):'))
        for row in rows:
            self.stdout.write(f'  {row}')
