from django.contrib import admin

from clipboard.models import ClipboardEntry


@admin.register(ClipboardEntry)
class ClipboardEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "device_id", "created_at")
    search_fields = ("device_id", "content")
    ordering = ("-created_at", "-id")
