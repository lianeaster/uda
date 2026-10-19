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
    path('groups/add/', views.GroupCreateView.as_view(), name='group_add'),
    path('groups/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/edit/', views.GroupUpdateView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),
    path('groups/<int:pk>/subjects/add/', views.GroupSubjectCreateView.as_view(), name='group_subject_add'),
    path('groups/<int:pk>/subjects/fill/', views.GroupSubjectsFillView.as_view(), name='group_subjects_fill'),
    path('group-subjects/<int:pk>/edit/', views.GroupSubjectUpdateView.as_view(), name='group_subject_edit'),
    path('group-subjects/<int:pk>/delete/', views.GroupSubjectDeleteView.as_view(), name='group_subject_delete'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('modules/add/', views.ModuleCreateView.as_view(), name='module_add'),
    path('modules/<int:pk>/', views.ModuleDetailView.as_view(), name='module_detail'),
    path('modules/<int:pk>/edit/', views.ModuleUpdateView.as_view(), name='module_edit'),
    path('modules/<int:pk>/delete/', views.ModuleDeleteView.as_view(), name='module_delete'),
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/<int:pk>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    path('subjects/add/', views.SubjectFormView.as_view(), name='subject_add'),
    path('subjects/<int:pk>/edit/', views.SubjectFormView.as_view(), name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
]
