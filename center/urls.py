from django.urls import path
from django.views.generic import RedirectView

from . import views
from .pages import PAGES

app_name = 'center'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    # Типові сторінки — з `pages.PAGES`: адреса й ім'я беруться звідти.
    *[path(page['path'], views.PageView.as_view(page=name), name=name)
      for name, page in PAGES.items()],
    path('news/', views.NewsView.as_view(), name='news'),
    path('news/<slug:slug>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('contacts/', views.ContactsView.as_view(), name='contacts'),
    path('food-academy/', views.FoodAcademyView.as_view(), name='food_academy'),
    # До переформатування це була сторінка академій за напрямами.
    path('directions/', RedirectView.as_view(pattern_name='center:services', permanent=True)),
]
