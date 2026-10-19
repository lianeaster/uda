from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.TaskListView.as_view(), name='list'),
    path('add/', views.TaskCreateView.as_view(), name='add'),
    path('<int:pk>/done/', views.TaskDoneView.as_view(), name='done'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='delete'),
]
