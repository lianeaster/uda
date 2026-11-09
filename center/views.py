from django.shortcuts import get_object_or_404, render
from django.views import View

from . import content, pages
from .forms import CenterContactForm, FoodAcademyContactForm
from .models import News

TITLE = content.NAME


def plan_context():
    """Усе, що потрібно плану приміщення (`center/includes/floor-plan.html`)."""
    return {
        'directions': content.DIRECTIONS,
        'plan': content.PLAN,
        'plan_rooms': content.PLAN_ROOMS,
        'plan_kinds': content.PLAN_KINDS,
    }


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


class HomeView(View):
    """Головна Центру: що він робить, для кого і як іде проєкт.

    Форми тут немає — кожна кнопка веде на «Контакти».
    """

    def get(self, request):
        return render(request, 'center/home.html', {
            'page_title': f'{TITLE} — UFIC',
            'page_description': pages.HOME['description'],
            'home': pages.HOME,
            'directions': content.DIRECTIONS,
            'news': News.objects.filter(is_published=True)[:3],
        })


class PageView(View):
    """Типова сторінка Центру: інтро й секції з `pages.PAGES[page]`."""

    page = None

    def get(self, request):
        page = pages.PAGES[self.page]
        ctx = {
            'page_title': f'{page["kicker"]} — {TITLE}',
            'page_description': page['description'],
            'page': page,
        }
        kinds = {section['kind'] for section in page['sections']}
        if 'plan' in kinds:
            ctx.update(plan_context())
        if 'academies' in kinds:
            ctx['academies'] = content.ACADEMIES
        return render(request, 'center/page.html', ctx)


class NewsView(View):
    def get(self, request):
        news = pages.NEWS
        rubrics = [{'title': label, 'text': news['rubrics'][value]}
                   for value, label in News.Rubric.choices]
        return render(request, 'center/news.html', {
            'page_title': f'{news["kicker"]} — {TITLE}',
            'page_description': news['description'],
            'page': news,
            'rubrics': rubrics,
            'posts': News.objects.filter(is_published=True),
        })


class NewsDetailView(View):
    def get(self, request, slug):
        post = get_object_or_404(News, slug=slug, is_published=True)
        return render(request, 'center/news_detail.html', {
            'page_title': f'{post.title} — {TITLE}',
            'page_description': post.summary,
            'post': post,
        })


class ContactsView(ContactPageView):
    """«Контакти»: звернення до Центру. Кнопки сторінок передають тему (`?tema=`)."""

    template_name = 'center/contacts.html'
    form_class = CenterContactForm

    def page_context(self):
        page = pages.CONTACTS
        ctx = {
            'page_title': f'{page["kicker"]} — {TITLE}',
            'page_description': page['description'],
            'page': page,
        }
        topic = dict(pages.TOPICS).get(self.request.GET.get('tema'))
        if topic:
            ctx['form'] = self.form_class(initial={'interest': topic})
        return ctx


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
