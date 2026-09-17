import datetime as dt

from django.shortcuts import render
from django.views import View

from . import content
from .forms import ContactRequestForm


def _next_intake():
    today = dt.date.today()
    year = today.year if today.month < 11 else today.year + 1
    return dt.date(year, 11, 15).strftime('%d.%m.%Y')


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
