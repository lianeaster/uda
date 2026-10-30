import datetime as dt

from django.http import Http404
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views import View

from schedule import programs
from schedule.pricing import public_prices

from . import content
from .forms import ConstructorRequestForm, ContactRequestForm


def _next_intake():
    today = dt.date.today()
    year = today.year if today.month < 11 else today.year + 1
    return dt.date(year, 11, 15).strftime('%d.%m.%Y')


def course_url(course_id):
    """Адреса сторінки курсу; у майстер-класів сторінки немає — ''."""
    page = content.COURSE_PAGES.get(course_id)
    return reverse('core:course', args=[page['slug']]) if page else ''


def constructor_catalog():
    """Картки готових курсів за id з матриці: назва, опис, фото, сторінка."""
    def card(item, kind, text):
        return {
            'id': item['id'], 'kind': kind, 'title': item['title'], 'text': text,
            'image': static('img/' + item['image']) if item.get('image') else '',
            'icon': item.get('icon', ''),
            'url': course_url(item['id']),
        }
    flagship = content.FLAGSHIP
    return (
        [card(flagship, 'program', flagship['lead'])]
        + [card(c, 'workshop', c['short']) for c in content.COURSES]
        + [card(m, 'masterclass', m['text']) for m in content.MASTERCLASSES]
    )


def linked(courses):
    """Картки курсів з адресою їхньої сторінки (`url`)."""
    return [{**c, 'url': course_url(c['id'])} for c in courses]


class HomeView(View):
    template_name = 'core/home.html'

    def get(self, request):
        return render(request, self.template_name, {
            # Заголовок і опис — тут, а не в шаблоні: той самий рядок іде і в
            # <title>, і в прев'ю посилання (див. `templates/base.html`).
            'page_title': 'Українська Академія Дистиляції',
            'page_description': content.DESCRIPTION,
            'next_intake': _next_intake(),
            'audience': content.AUDIENCE,
            'flagship': linked([content.FLAGSHIP])[0],
            'promo_video': content.PROMO_VIDEO,
            'courses': linked(content.COURSES[:4]),
            # Усі лектори — стрічкою, що повільно пливе (див. home.html).
            'lecturers': lecturer_cards(content.LECTURERS),
            'testimonial_videos': content.TESTIMONIAL_VIDEOS,
            'services': content.SERVICES,
            'partners': content.PARTNERS,
            'news': content.NEWS,
            # Герой головної — конструктор курсів; заявку з нього приймає
            # ConstructorView, тут лише форма й картки.
            'catalog': constructor_catalog(),
            'prices': public_prices(),
            'form': ConstructorRequestForm(),
            'graduates': graduate_photos(),
        })


class CoursesView(View):
    template_name = 'core/courses.html'

    def get(self, request):
        return render(request, self.template_name, {
            'page_title': 'Курси та майстерні — Українська Академія Дистиляції',
            'page_description': (
                'Сертифікаційна програма «Майстер дистиляції» та майстерні: зернові '
                'дистиляти, віскі, джин, витримка, сенсорний аналіз і хімія бродіння.'
            ),
            'next_intake': _next_intake(),
            'flagship': linked([content.FLAGSHIP])[0],
            'promo_video': content.PROMO_VIDEO,
            'courses': linked(content.COURSES),
            'masterclasses': content.MASTERCLASSES,
        })


# Нахили фотокарток по черзі — як знімки, розкладені на столі. Нахил іде з
# карткою, а не з її місцем у сітці: у стрічці на головній картки повторюються,
# і на шві повтору нахил не має перескакувати.
TILTS = ['-1.2deg', '1deg', '-0.4deg', '0.8deg']


def lecturer_cards(people):
    """Картки лекторів-фотокартки: прямокутний портрет і фото, що визирає з-під нього."""
    cards = []
    for i, person in enumerate(people):
        gallery = content.LECTURER_PAGES.get(person['slug'], {}).get('gallery', [])
        cards.append({**person, 'portrait': person['photo'],
                      'behind': 'lecturers/' + gallery[0][0] if gallery else '',
                      'tilt': TILTS[i % len(TILTS)]})
    return cards


def graduate_photos(course_id=None):
    """Фото пляшок випускників; з `course_id` — лише тих, хто пройшов цей курс.

    Бренди йдуть по черзі, щоб дві пляшки одного виробника не стояли поруч.
    """
    graduates = [g for g in content.GRADUATES if course_id is None or course_id in g['courses']]
    queues = [[{'src': 'graduates/' + src, 'image': static('img/graduates/' + src),
                'brand': g['brand'], 'url': g['link'][1]}
               for src, _source in g['photos']] for g in graduates]
    photos = []
    while any(queues):
        for queue in queues:
            if queue:
                photos.append(queue.pop(0))
    for i, photo in enumerate(photos):
        photo['tilt'] = TILTS[i % len(TILTS)]
    return photos


def master_plan():
    """План «Майстра» — модулі й предмети його програми, як у графіку групи."""
    for code, name, module_format, items in programs.MODULES:
        yield (f'Модуль {code}. {name.rstrip(".")} · {module_format}',
               [subject for _code, subject, _lecturers, _hours in items])


class CourseView(View):
    """Сторінка одного курсу Академії: опис, програма, лектори й запис.

    Дані — `content.COURSE_PAGES` і картка курсу з `content.COURSES` /
    `FLAGSHIP`. Заявка йде в ту саму таблицю, що й консультації, а курс у ній
    підписує сервер, не форма.
    """

    template_name = 'core/course.html'
    slugs = {page['slug']: course_id for course_id, page in content.COURSE_PAGES.items()}

    def _course(self, slug):
        course_id = self.slugs.get(slug)
        if course_id is None:
            raise Http404
        page = content.COURSE_PAGES[course_id]
        if course_id == content.FLAGSHIP['id']:
            card, name, kind = content.FLAGSHIP, programs.COURSE, 'Сертифікаційна програма'
            course_format, start, plan = 'Онлайн / Офлайн', _next_intake(), list(master_plan())
        else:
            card = next(c for c in content.COURSES if c['id'] == course_id)
            name, kind, course_format = card['title'], card['tag'], card['format']
            # Дата зі старого сайту, що вже минула, — не старт наступного потоку.
            start = page.get('start')
            start = start.strftime('%d.%m.%Y') if start and start >= dt.date.today() else None
            plan = page.get('plan', [])
        return {
            **page, 'id': course_id, 'name': name, 'kind': kind, 'format': course_format,
            'start': start, 'plan': plan, 'image': card['image'], 'lead': card.get('text', card.get('lead')),
            'price_eur': card['price_eur'], 'early_bird_eur': card.get('early_bird_eur'),
            'lecturers': lecturer_cards([content.LECTURERS_BY_SLUG[s] for s in page['lecturers']]),
            'audience': page.get('audience', content.AUDIENCE),
        }

    def _context(self, course, **extra):
        others = [c for c in content.COURSES if c['id'] != course['id']][:3]
        ctx = {
            'page_title': f'{course["name"]} — Українська Академія Дистиляції',
            'page_description': course['lead'],
            'course': course,
            # Кілька фото — щоб блок був доказом, а не ще однією галереєю.
            'graduates': graduate_photos(course['id'])[:5],
            'others': linked(others),
            'form': ContactRequestForm(),
        }
        ctx.update(extra)
        return ctx

    def get(self, request, slug):
        course = self._course(slug)
        return render(request, self.template_name,
                      self._context(course, submitted='done' in request.GET))

    def post(self, request, slug):
        course = self._course(slug)
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.interest = f'Запис на курс «{course["name"]}»'
            enquiry.save()
            # Як і в конструкторі: оновлення подяки не надсилає заявку вдруге.
            return redirect(reverse('core:course', args=[slug]) + '?done=1#zayavka')
        return render(request, self.template_name, self._context(course, form=form))


# Логін на платформі, що не збігається зі slug картки лектора на сайті.
PLATFORM_LOGINS = {'manager': 'kateryna-kamysheva'}


def master_topics(slug):
    """Предмети «Майстра», які веде лектор, — за графіком групи (`schedule.programs`)."""
    for _code, _name, _format, items in programs.MODULES:
        for _subject_code, subject, signatures, _hours in items:
            logins = {programs.LECTURERS[s][0] for s in signatures}
            if slug in {PLATFORM_LOGINS.get(login, login) for login in logins}:
                yield subject


class LecturerView(View):
    """Сторінка лектора: стос фото, біографія, курси, які веде, і теми в «Майстрі»."""

    template_name = 'core/lecturer.html'

    def get(self, request, slug):
        person = content.LECTURERS_BY_SLUG.get(slug)
        if person is None:
            raise Http404
        page = content.LECTURER_PAGES.get(slug, {})
        courses = [c for c in [content.FLAGSHIP, *content.COURSES]
                   if slug in content.COURSE_PAGES[c['id']]['lecturers']]
        # Сусіди за списком, по колу: щоб з кожної сторінки вели інші.
        at = content.LECTURERS.index(person)
        others = [content.LECTURERS[(at + i) % len(content.LECTURERS)] for i in range(1, 5)]
        return render(request, self.template_name, {
            'page_title': f'{person["name"]} — лектор Української Академії Дистиляції',
            'page_description': person['bio'],
            'person': person,
            'about': page.get('about', [person['bio']]),
            # Стос фото: зверху портрет з картки, під ним — фото з джерел.
            'photos': [person['photo'],
                       *('lecturers/' + src for src, _source in page.get('gallery', []))],
            'courses': linked(courses),
            'master_topics': list(master_topics(slug)),
            'others': lecturer_cards(others),
        })


class ConstructorView(View):
    """Конструктор курсів — публічний, без входу.

    Підбір рахує скрипт на матриці компетенцій (static/js/course-engine.js);
    звідси сторінка бере картки курсів із сайту, ціни з платформи
    (`schedule.pricing.public_prices`) і приймає заявку. Той
    самий віджет стоїть у героя головної й шле заявку сюди ж.
    """

    template_name = 'core/constructor.html'

    def _context(self, **extra):
        ctx = {
            'page_title': 'Конструктор курсів — Українська Академія Дистиляції',
            'page_description': (
                'Зберіть свій курс за хвилину: три запитання — і ви бачите '
                'індивідуальну програму та готові курси Академії з відсотком, '
                'наскільки вони вам підходять.'
            ),
            'catalog': constructor_catalog(),
            'prices': public_prices(),
            'form': ConstructorRequestForm(),
        }
        ctx.update(extra)
        return ctx

    def get(self, request):
        return render(request, self.template_name,
                      self._context(submitted='done' in request.GET))

    def post(self, request):
        form = ConstructorRequestForm(request.POST)
        if form.is_valid():
            form.save()
            # Редирект, а не сторінка у відповідь: оновлення подяки не має
            # надсилати заявку вдруге.
            return redirect(reverse('core:constructor') + '?done=1')
        return render(request, self.template_name, self._context(form=form))


class LecturersView(View):
    template_name = 'core/lecturers.html'

    def _context(self, **extra):
        ctx = {
            'page_title': 'Лектори — Українська Академія Дистиляції',
            'page_description': (
                'Технологи, науковці, крафтові виробники, сомельє та юристи галузі — '
                'ті, хто читає курси Академії.'
            ),
            'lecturers': lecturer_cards(content.LECTURERS),
            'form': ContactRequestForm(),
        }
        ctx.update(extra)
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._context())

    def post(self, request):
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, self.template_name, self._context(submitted=True))
        return render(request, self.template_name, self._context(form=form))
