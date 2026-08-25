from django.contrib import admin

from clipboard.models import ClipboardEntry, ClipboardState, Device, PairingCode


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "device_id", "device_type", "created_at", "updated_at")
    list_filter = ("device_type", "created_at")
    search_fields = ("device_id", "user__username")
    ordering = ("-created_at",)


@admin.register(ClipboardState)
class ClipboardStateAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "content", "updated_at", "expires_at")
    search_fields = ("user__username", "content")
    ordering = ("-updated_at",)


@admin.register(PairingCode)
class PairingCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "desktop_device", "created_at", "expires_at", "is_used", "used_at")
    list_filter = ("is_used", "created_at")
    search_fields = ("code", "desktop_device__device_id", "desktop_device__user__username")
    ordering = ("-created_at",)


@admin.register(ClipboardEntry)
class ClipboardEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "device_id", "created_at")
    search_fields = ("device_id", "content")
    ordering = ("-created_at", "-id")
