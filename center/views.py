from django.shortcuts import render
from django.views import View

from . import content
from .forms import CenterContactForm, FoodAcademyContactForm

TITLE = content.NAME


class ContactPageView(View):
    """Сторінка із заявкою внизу: показати, прийняти, подякувати на місці."""

    template_name = None
    form_class = None

    def page_context(self):
        return {}

    def _context(self, **extra):
        ctx = self.page_context()
        ctx.setdefault('form', self.form_class())
        ctx.update(extra)
        return ctx

    def get(self, request):
        return render(request, self.template_name, self._context())

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return render(request, self.template_name, self._context(submitted=True))
        return render(request, self.template_name, self._context(form=form))


class HomeView(ContactPageView):
    """Головна Центру: що він робить (послуги), для кого і де — і дві академії."""

    template_name = 'center/home.html'
    form_class = CenterContactForm

    def page_context(self):
        return {
            'page_title': f'{TITLE} — UFIC',
            'page_description': content.DESCRIPTION,
            'path': content.PATH,
            'farmer_case': content.FARMER_CASE,
            'directions': content.DIRECTIONS,
            'services': content.SERVICES,
            'incubator': content.INCUBATOR,
            'academies': content.ACADEMIES,
            'plan': content.PLAN,
            'plan_rooms': content.PLAN_ROOMS,
            'plan_kinds': content.PLAN_KINDS,
            'plan_area': content.PLAN_AREA,
        }


class ServicesView(View):
    template_name = 'center/services.html'

    def get(self, request):
        return render(request, self.template_name, {
            'page_title': f'Послуги — {TITLE}',
            'page_description': (
                'Дослідження сировини, консалтинг і розробка продукту, прототипи '
                'та пілотні партії, комерціалізація, переробка побічної сировини — '
                'і дві академії: дистиляції та харчових інновацій.'
            ),
            'services': content.SERVICES,
            'incubator': content.INCUBATOR,
            'academies': content.ACADEMIES,
        })


class FoodAcademyView(ContactPageView):
    """Сторінка харчової академії — у бренді Центру, бо свого в неї немає."""

    template_name = 'center/food_academy.html'
    form_class = FoodAcademyContactForm

    def page_context(self):
        academy = content.FOOD_ACADEMY
        directions = content.FOOD_DIRECTIONS
        ctx = {
            'page_title': f'{academy["name"]} — {TITLE}',
            'page_description': academy['description'],
            'academy': academy,
            'directions': directions,
            'topics_count': sum(len(d['topics']) for d in directions),
            'sibling': content.ACADEMIES[0],
            'platform': content.PLATFORM,
            'plan_area': content.PLAN_AREA,
        }
        # «Хочу в першу групу» на картці напряму веде до форми з ним у полі.
        chosen = {d['slug']: d for d in directions}.get(self.request.GET.get('napryam'))
        if chosen:
            ctx['form'] = self.form_class(initial={'interest': chosen['title']})
        return ctx
