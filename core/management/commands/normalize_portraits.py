"""Зводить портрети лекторів до одного вигляду.

Оригінали — знімки з різних місць і різних років: хтось у студії, хтось на
вулиці, хтось зі сцени з мікрофоном. Поряд на сторінці це читається як
фотоальбом, а не як склад Академії.

Колір лишається кольором: лендінг увесь у кольорових фото й відео, і
монохромні портрети серед них виглядали б чужими. Зводимо те, що справді
розсинхронізоване, — експозицію, контраст і масштаб голови в кадрі.

Джерело — `static/img/lecturers/source/`, результат — `static/img/lecturers/`.
Оригінали не змінюються, тож обробку завжди можна перерахувати заново.

Портрет — вертикальна фотокартка 4:5 (так їх показує сайт), а не коло:
оригінали — круглі вирізки, тож беремо найбільший прямокутник, що вміщується
в коло джерела.
"""

import math

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageChops

SIZE = 520          # кадр по колу джерела, з якого вирізаємо портрет
PORTRAIT = (640, 800)   # фотокартка 4:5, як у стосі й у сітках лекторів
QUALITY = 88

# Цільова світлота обличчя (0-255) і смуга гами, за яку не виходимо.
FACE_TARGET = 152
GAMMA_LIMITS = (0.6, 1.7)
# Каст освітлення не чіпаємо: корекція «сірого світу» вимивала теплі тони
# шкіри, а заодно фарбувала біле тло джерела в холодне.
# Розтягнення яскравості: однакове для всіх каналів, інакше поїде колір.
CLIP_PERCENT = 0.01
OUTPUT_RANGE = (6, 250)

# Базовий зум трохи підтягує кадр (оригінали — кола з повітрям по краях).
# Далі — виправлення для тих, хто помітно вибивається з ряду: у звіті команди
# видно, кого саме підтягнуто.
BASE_ZOOM = 1.0     # рівно коло джерела
FRAMING = {
    # слаг:              (зум, зсув по X, зсув по Y) — зсув у частках кадру.
    # Прямокутник усередині кола й так кадрує щільніше, ніж коло, тож
    # підтягуємо лише тих, хто знятий здалеку.
    'evgen-zavertany':    (1.06, 0.0, -0.03),   # знято здалеку, голова дрібна
    'tymur-razjabov':     (1.04, -0.03, -0.04),  # загальний план із келихом
}


def content_box(image):
    """Межі самого кола на білому тлі файлу.

    Білі поля в оригіналах різні (⌀401 із 480 у більшості, ⌀334 у двох), тож
    відштовхуватися від краю файлу не можна: у когось лишалося б біле кільце,
    а голови стояли б у різному масштабі.
    """
    white = Image.new('RGB', image.size, (255, 255, 255))
    difference = ImageChops.difference(image, white).convert('L')
    return difference.point(lambda v: 255 if v > 17 else 0).getbbox()


def frame(image, zoom, dx, dy):
    """Квадратний кадр по колу джерела; зум >1 обрізає далі до центру."""
    box = content_box(image) or (0, 0, image.width, image.height)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    side = max(box[2] - box[0], box[3] - box[1]) / zoom
    cx += dx * side
    cy += dy * side
    left = max(0, min(image.width - side, cx - side / 2))
    top = max(0, min(image.height - side, cy - side / 2))
    crop = (round(left), round(top), round(left + side), round(top + side))
    return image.resize((SIZE, SIZE), Image.LANCZOS, box=crop)


def centre(image):
    """Ділянка, де на портреті обличчя, — по ній рівняємо світло й колір."""
    side = image.width
    return image.crop((side // 4, side // 5, side * 3 // 4, side * 4 // 5))


def stretch_range(image):
    """Розтягує яскравість у спільний діапазон — однаково для трьох каналів.

    Per-channel `autocontrast` зробив би те саме, але заодно посунув би колір:
    у знімку з жовтою стіною він витягнув би синій канал і вибілив каст, якого
    ми ще не вирішили, чи прибирати.
    """
    histogram = image.convert('L').histogram()
    total = sum(histogram)
    clip = total * CLIP_PERCENT
    low, high, run = 0, 255, 0
    for value, count in enumerate(histogram):
        run += count
        if run > clip:
            low = value
            break
    run = 0
    for value in range(255, -1, -1):
        run += histogram[value]
        if run > clip:
            high = value
            break
    if high - low < 16:          # майже пласке зображення — не чіпаємо
        return image
    lo_out, hi_out = OUTPUT_RANGE
    scale = (hi_out - lo_out) / (high - low)
    table = [max(0, min(255, round(lo_out + (i - low) * scale))) for i in range(256)]
    return image.point(table * 3)


def normalize_light(image):
    """Гамою виводить світлоту обличчя на `FACE_TARGET`.

    Гама, а не яскравість: вона тягне середні тони, не з'їдаючи ні глибину в
    тінях, ні деталі в світлому. Рівняємо центр кадру, а не весь знімок, —
    інакше темний піджак або світла стіна тягнули б обличчя за собою.
    """
    pixels = list(centre(image).convert('L').getdata())
    mean = sum(pixels) / len(pixels)
    if mean <= 1 or mean >= 254:
        return image
    gamma = math.log(FACE_TARGET / 255) / math.log(mean / 255)
    gamma = max(GAMMA_LIMITS[0], min(GAMMA_LIMITS[1], gamma))
    table = [round(255 * (i / 255) ** gamma) for i in range(256)]
    return image.point(table * 3)


def inscribed_portrait(image):
    """Найбільший прямокутник 4:5 усередині кола кадру — без білих кутів.

    Діагональ прямокутника дорівнює діаметру кола; 2% запасу — на згладжений
    край кола джерела.
    """
    width, height = PORTRAIT
    diameter = image.width * 0.98
    scale = diameter / math.hypot(width, height)
    w, h = width * scale, height * scale
    cx = cy = image.width / 2
    box = (round(cx - w / 2), round(cy - h / 2), round(cx + w / 2), round(cy + h / 2))
    return image.resize(PORTRAIT, Image.LANCZOS, box=box)


class Command(BaseCommand):
    help = 'Зводить портрети лекторів (static/img/lecturers/source/) до одного вигляду.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Показати, що буде зроблено, нічого не записуючи.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        quiet = options['verbosity'] == 0
        folder = settings.BASE_DIR / 'static' / 'img' / 'lecturers'
        source = folder / 'source'
        if not source.is_dir():
            self.stderr.write(self.style.ERROR(f'Немає теки з оригіналами: {source}'))
            return

        done = []
        for path in sorted(source.glob('*.jpg')):
            zoom, dx, dy = FRAMING.get(path.stem, (BASE_ZOOM, 0.0, 0.0))
            with Image.open(path) as original:
                image = frame(original.convert('RGB'), zoom, dx, dy)
                image = normalize_light(stretch_range(image))
                image = inscribed_portrait(image)
            target = folder / f'{path.stem}.jpg'
            if not dry_run:
                image.save(target, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
            note = '' if path.stem not in FRAMING else f' (кадр підтягнуто: зум {zoom})'
            done.append(f'{target.name} — {PORTRAIT[0]}×{PORTRAIT[1]}{note}')

        if not quiet:
            prefix = '[--dry-run] ' if dry_run else ''
            self.stdout.write(self.style.SUCCESS(f'{prefix}Оброблено портретів: {len(done)}'))
            for row in done:
                self.stdout.write(f'  {row}')
