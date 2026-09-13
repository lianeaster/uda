from django.contrib import admin

from .models import Course, ScheduleEntry, Subject


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'teacher', 'source', 'title')
    list_filter = ('source', 'teacher')
    date_hierarchy = 'date'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'course')
    list_filter = ('course',)
    filter_horizontal = ('teachers',)
