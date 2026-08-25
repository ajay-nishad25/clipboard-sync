from django.contrib import admin

from clipboard.models import ClipboardEntry, ClipboardState, Device, DeviceCredential, PairingCode


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "device_id", "device_type", "created_at", "updated_at")
    list_filter = ("device_type", "created_at")
    search_fields = ("device_id", "user__username")
    ordering = ("-created_at",)


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "token_hash_preview", "created_at", "last_used_at", "revoked_at", "is_active")
    list_filter = ("revoked_at", "created_at")
    search_fields = ("device__device_id", "device__user__username", "token_hash")
    ordering = ("-created_at",)
    actions = ["revoke_credentials"]

    def token_hash_preview(self, obj: DeviceCredential) -> str:
        return f"{obj.token_hash[:12]}..." if obj.token_hash else ""
    token_hash_preview.short_description = "Token Hash (SHA-256)"

    def is_active(self, obj: DeviceCredential) -> bool:
        return obj.is_active()
    is_active.boolean = True

    @admin.action(description="Revoke selected device credentials")
    def revoke_credentials(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(revoked_at=timezone.now())
        self.message_user(request, f"{updated} credential(s) revoked successfully.")
