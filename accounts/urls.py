from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('account/', views.AccountView.as_view(), name='account'),
    path('account/password/', views.PasswordChangeView.as_view(), name='password_change'),
    path('people/', views.PersonListView.as_view(), name='person_list'),
    path('people/<int:pk>/', views.PersonDetailView.as_view(), name='person_detail'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
]
