from django.urls import path

from . import views

app_name = 'schedule'

urlpatterns = [
    path('', views.ScheduleView.as_view(), name='home'),
    path('add/', views.ScheduleEntryCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.ScheduleEntryUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ScheduleEntryDeleteView.as_view(), name='delete'),
    path('<int:pk>/accept/', views.ScheduleEntryReviewView.as_view(
        decision='accepted'), name='accept'),
    path('<int:pk>/reject/', views.ScheduleEntryReviewView.as_view(
        decision='rejected'), name='reject'),
    path('proposals/', views.ProposalListView.as_view(), name='proposal_list'),
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/subjects/add/', views.GroupSubjectCreateView.as_view(), name='group_subject_add'),
    path('groups/<int:pk>/subjects/fill/', views.GroupSubjectsFillView.as_view(), name='group_subjects_fill'),
    path('group-subjects/<int:pk>/delete/', views.GroupSubjectDeleteView.as_view(), name='group_subject_delete'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/add/', views.SubjectCreateView.as_view(), name='subject_add'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
]
