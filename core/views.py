import datetime as dt

from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views import View

from schedule.pricing import public_prices

from . import content
from .forms import ConstructorRequestForm, ContactRequestForm


def _next_intake():
    today = dt.date.today()
    year = today.year if today.month < 11 else today.year + 1
    return dt.date(year, 11, 15).strftime('%d.%m.%Y')


def constructor_catalog():
    """Картки готових курсів за id з матриці: назва, опис, фото."""
    def card(item, kind, text):
        return {
            'id': item['id'], 'kind': kind, 'title': item['title'], 'text': text,
            'image': static('img/' + item['image']) if item.get('image') else '',
            'icon': item.get('icon', ''),
        }
    flagship = content.FLAGSHIP
    return (
        [card(flagship, 'program', flagship['lead'])]
        + [card(c, 'workshop', c['short']) for c in content.COURSES]
        + [card(m, 'masterclass', m['text']) for m in content.MASTERCLASSES]
    )


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
            'flagship': content.FLAGSHIP,
            'promo_video': content.PROMO_VIDEO,
            'courses': content.COURSES[:4],
            'lecturers': content.FEATURED_LECTURERS,
            'testimonial_videos': content.TESTIMONIAL_VIDEOS,
            'services': content.SERVICES,
            'partners': content.PARTNERS,
            'news': content.NEWS,
            # Герой головної — конструктор курсів; заявку з нього приймає
            # ConstructorView, тут лише форма й картки.
            'catalog': constructor_catalog(),
            'prices': public_prices(),
            'form': ConstructorRequestForm(),
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
            'flagship': content.FLAGSHIP,
            'promo_video': content.PROMO_VIDEO,
            'courses': content.COURSES,
            'masterclasses': content.MASTERCLASSES,
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
            'lecturers': content.LECTURERS,
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
