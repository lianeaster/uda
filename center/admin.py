from django.contrib import admin

from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'rubric', 'date', 'is_published')
    list_filter = ('rubric', 'is_published')
    list_editable = ('is_published',)
    search_fields = ('title', 'summary', 'body')
    prepopulated_fields = {'slug': ('title',)}
