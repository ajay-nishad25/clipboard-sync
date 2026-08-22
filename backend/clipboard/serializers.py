from rest_framework import serializers

from clipboard.models import ClipboardEntry


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
