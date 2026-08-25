from __future__ import annotations

from rest_framework import serializers

from clipboard.models import ClipboardEntry, ClipboardState, Device


class TextOnlyField(serializers.CharField):
    """Reject JSON values that are not strings instead of coercing them."""

    default_error_messages = {"invalid": "Content must be a text string."}

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(self.error_messages["invalid"], code="invalid")
        return super().to_internal_value(data)


class ClipboardEntrySerializer(serializers.ModelSerializer):
    content = TextOnlyField(allow_blank=False)

    class Meta:
        model = ClipboardEntry
        fields = ("id", "device_id", "content", "created_at")
        read_only_fields = ("id", "created_at")


class ClipboardStateSerializer(serializers.ModelSerializer):
    content = TextOnlyField(allow_blank=False)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ClipboardState
        fields = ("user_id", "username", "content", "updated_at", "expires_at")
        read_only_fields = ("user_id", "username", "updated_at", "expires_at")


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("id", "user", "device_id", "device_type", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
