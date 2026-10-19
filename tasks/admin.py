from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('due_date', 'title', 'assignee', 'remind_on', 'done_at')
    list_filter = ('done_at',)
    date_hierarchy = 'due_date'
    search_fields = ('title', 'notes')
    readonly_fields = ('key', 'done_at', 'done_by', 'created_by')
