from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='home'),
    path('competencies/', views.CompetencyMatrixView.as_view(), name='competencies'),
]
