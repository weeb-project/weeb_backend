from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Configuration admin pour suivre les messages de contact."""
    list_display = ['first_name', 'last_name', 'email', 'subject', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'subject']
    readonly_fields = ['first_name', 'last_name', 'email', 'subject', 'message', 'created_at']
    actions = ['mark_as_read']

    @admin.action(description='Marquer comme lu')
    def mark_as_read(self, request, queryset):
        """Marque les messages sélectionnés comme lus."""
        queryset.update(is_read=True)
