from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'center'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('services/', views.ServicesView.as_view(), name='services'),
    path('food-academy/', views.FoodAcademyView.as_view(), name='food_academy'),
    # До переформатування це була сторінка академій за напрямами.
    path('directions/', RedirectView.as_view(pattern_name='center:services', permanent=True)),
]
