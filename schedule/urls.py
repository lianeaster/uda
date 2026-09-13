from django.urls import path

from . import views

app_name = 'schedule'

urlpatterns = [
    path('', views.ScheduleView.as_view(), name='home'),
    path('add/', views.ScheduleEntryCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.ScheduleEntryUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ScheduleEntryDeleteView.as_view(), name='delete'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_add'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
]
