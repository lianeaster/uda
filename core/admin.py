from django.contrib import admin

from .models import ContactRequest


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'interest', 'source', 'created_at')
    list_filter = ('source',)
    readonly_fields = ('created_at',)
