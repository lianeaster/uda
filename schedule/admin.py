from django.contrib import admin

from .models import Course, Enrollment, Group, GroupSubject, ScheduleEntry, Subject


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'group', 'title', 'teacher',
                    'source', 'status')
    list_filter = ('source', 'status', 'group')
    date_hierarchy = 'date'
    # `title` і `teacher` — обчислювані, тож лише для читання в списку.
    readonly_fields = ('reviewed_by', 'reviewed_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'group__course', 'group_subject__subject', 'group_subject__teacher')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'course')
    list_filter = ('course',)
    search_fields = ('name',)
    filter_horizontal = ('teachers',)


class GroupSubjectInline(admin.TabularInline):
    model = GroupSubject
    extra = 1
    autocomplete_fields = ('subject', 'teacher')


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 1
    autocomplete_fields = ('student',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'start_date', 'end_date')
    list_filter = ('course',)
    search_fields = ('name',)
    inlines = (GroupSubjectInline, EnrollmentInline)


@admin.register(GroupSubject)
class GroupSubjectAdmin(admin.ModelAdmin):
    list_display = ('group', 'subject', 'teacher', 'start_date', 'end_date')
    list_filter = ('group', 'teacher')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'group', 'start_date', 'end_date')
    list_filter = ('group',)
