from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['first_name', 'last_name', 'email', 'phone', 'message', 'created_at']
    actions = ['mark_as_read']

    @admin.action(description='Marquer comme lu')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
