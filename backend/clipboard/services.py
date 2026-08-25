from __future__ import annotations

from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from clipboard.models import ClipboardState, Device, DeviceType


def resolve_device_and_user(
    device_id: str,
    default_type: str = DeviceType.DESKTOP,
) -> tuple[Device | None, User | None]:
    """Resolve a device_id string to its Device and User models.

    For development compatibility, auto-provisions a User and Device if device_id
    is not yet registered in the database.
    """
    if not device_id or not isinstance(device_id, str) or not device_id.strip():
        return None, None

    device_id = device_id.strip()
    try:
        device = Device.objects.select_related("user").get(device_id=device_id)
        return device, device.user
    except Device.DoesNotExist:
        dtype = DeviceType.ANDROID if "android" in device_id.lower() else default_type
        username = f"user_{device_id}"
        user, _ = User.objects.get_or_create(username=username)
        device = Device.objects.create(user=user, device_id=device_id, device_type=dtype)
        return device, user


def set_user_clipboard(user: User, content: str, ttl_minutes: int = 10) -> ClipboardState:
    """Set or replace the single active ClipboardState for *user* with a 10-minute expiration."""
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    state, created = ClipboardState.objects.get_or_create(
        user=user,
        defaults={"content": content, "expires_at": expires_at},
    )
    if not created:
        state.content = content
        state.expires_at = expires_at
        state.save()
    return state


def get_active_user_clipboard(user: User) -> ClipboardState | None:
    """Return the active ClipboardState for *user*, automatically deleting it if expired."""
    state = ClipboardState.objects.filter(user=user).first()
    if state is None:
        return None

    if state.is_expired():
        state.delete()
        return None

    return state
