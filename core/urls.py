from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('courses/', views.CoursesView.as_view(), name='courses'),
    path('lecturers/', views.LecturersView.as_view(), name='lecturers'),
]
