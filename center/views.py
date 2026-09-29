from django.shortcuts import render
from django.views import View

from core import content as academy
from . import content
from .forms import CenterContactForm

TITLE = content.NAME


class HomeView(View):
    """Головна «парасолька»: карта Центру — академії, платформа, спільна база."""

    template_name = 'center/home.html'

    def _context(self, **extra):
        ctx = {
            'page_title': f'{TITLE} — UFIC',
            'page_description': content.DESCRIPTION,
            'path': content.PATH,
            'farmer_case': content.FARMER_CASE,
            'academies': content.ACADEMIES,
            'academy': content.ACADEMIES[0],
            'platform': content.PLATFORM,
            'base': content.BASE,
            # Цифри Академії беремо з її ж контенту, щоб не розходились.
            'academy_courses': len(academy.COURSES) + len(academy.MASTERCLASSES),
            'academy_lecturers': len(academy.LECTURERS),
            'academy_partners': len(academy.PARTNERS),
            'plan': content.PLAN,
            'plan_rooms': content.PLAN_ROOMS,
            'plan_kinds': content.PLAN_KINDS,
            'plan_area': content.PLAN_AREA,
            'form': CenterContactForm(),
        }
        ctx.update(extra)
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._context())

    def post(self, request):
        form = CenterContactForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, self.template_name, self._context(submitted=True))
        return render(request, self.template_name, self._context(form=form))


class DirectionsView(View):
    template_name = 'center/directions.html'

    def get(self, request):
        return render(request, self.template_name, {
            'page_title': f'Напрями — {TITLE}',
            'page_description': (
                'Академії дистиляції, безалкогольних напоїв, ферментації, снеків, '
                'функціональних продуктів і суперфудів, '
                'соусів, олій і борошна, вина й меду — з однією навчальною '
                'платформою та спільною виробничою базою.'
            ),
            'academies': content.ACADEMIES,
            'platform': content.PLATFORM,
            'units': content.BASE,
            'base': content.BASE,
            'incubator': content.INCUBATOR,
        })
