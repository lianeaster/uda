import datetime as dt

from django.shortcuts import render
from django.views import View

from .forms import ContactRequestForm


def _next_intake():
    today = dt.date.today()
    year = today.year if today.month < 11 else today.year + 1
    return dt.date(year, 11, 15).strftime('%d.%m.%Y')


TESTIMONIAL_VIDEOS = [
    'https://www.youtube.com/watch?v=dlQrEtZtuSo',
    'https://www.youtube.com/watch?v=zLiLN7L0cb4',
    'https://www.youtube.com/watch?v=PeV5h1hNLag',
    'https://www.youtube.com/watch?v=mxFGeoMvAFw',
]


class HomeView(View):
    template_name = 'core/home.html'

    def get(self, request):
        return render(request, self.template_name, {
            'next_intake': _next_intake(),
            'testimonial_videos': TESTIMONIAL_VIDEOS,
        })


class CoursesView(View):
    template_name = 'core/courses.html'

    def get(self, request):
        return render(request, self.template_name, {'next_intake': _next_intake()})


class LecturersView(View):
    template_name = 'core/lecturers.html'

    def get(self, request):
        return render(request, self.template_name, {'form': ContactRequestForm()})

    def post(self, request):
        form = ContactRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, self.template_name, {'form': ContactRequestForm(), 'submitted': True})
        return render(request, self.template_name, {'form': form})
