from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('courses/', views.CoursesView.as_view(), name='courses'),
    path('courses/<slug:slug>/', views.CourseView.as_view(), name='course'),
    path('constructor/', views.ConstructorView.as_view(), name='constructor'),
    path('lecturers/', views.LecturersView.as_view(), name='lecturers'),
    path('lecturers/<slug:slug>/', views.LecturerView.as_view(), name='lecturer'),
]
