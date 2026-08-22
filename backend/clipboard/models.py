from django.db import models


class ClipboardEntry(models.Model):
    """A text clipboard value received from a development device."""

    device_id = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.device_id}: {self.content[:50]}"
