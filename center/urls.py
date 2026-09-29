from django.urls import path

from . import views

app_name = 'center'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('directions/', views.DirectionsView.as_view(), name='directions'),
]
