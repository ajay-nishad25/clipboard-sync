from __future__ import annotations

import secrets
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from clipboard.models import ClipboardState, Device, DeviceType, PairingCode

# Alphabet excluding visually ambiguous characters: 0, O, 1, I, L
_PAIRING_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_pairing_code_str(length: int = 8) -> str:
    """Generate a cryptographically secure pairing code string in AB7K-29XM format."""
    chars = [secrets.choice(_PAIRING_ALPHABET) for _ in range(length)]
    half = length // 2
    return f"{''.join(chars[:half])}-{''.join(chars[half:])}"


def create_pairing_code(desktop_device: Device, ttl_minutes: int = 5) -> PairingCode:
    """Generate a unique temporary pairing code for a desktop device."""
    if desktop_device.device_type != DeviceType.DESKTOP:
        raise ValueError("Pairing codes can only be generated for desktop devices.")

    for _ in range(20):
        raw_code = generate_pairing_code_str()
        if not PairingCode.objects.filter(code=raw_code).exists():
            expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
            return PairingCode.objects.create(
                desktop_device=desktop_device,
                code=raw_code,
                expires_at=expires_at,
            )
    raise RuntimeError("Failed to generate a unique pairing code after multiple attempts.")


def pair_android_device(code_str: str, android_device_id: str) -> tuple[Device | None, str | None]:
    """Pair an Android device using a pairing code.

    Returns (android_device, None) on success, or (None, error_message) on failure.
    """
    if not code_str or not isinstance(code_str, str) or not code_str.strip():
        return None, "Pairing code is required."

    if not android_device_id or not isinstance(android_device_id, str) or not android_device_id.strip():
        return None, "Android device ID is required."

    normalized_code = code_str.strip().upper()
    if len(normalized_code) == 8 and "-" not in normalized_code:
        normalized_code = f"{normalized_code[:4]}-{normalized_code[4:]}"

    try:
        pairing_code = PairingCode.objects.select_related("desktop_device__user").get(code=normalized_code)
    except PairingCode.DoesNotExist:
        return None, "Invalid or unknown pairing code."

    if pairing_code.is_used:
        return None, "Pairing code has already been used."

    if timezone.now() >= pairing_code.expires_at:
        return None, "Pairing code has expired."

    desktop_device = pairing_code.desktop_device
    if desktop_device.device_type != DeviceType.DESKTOP:
        return None, "Pairing code does not belong to a desktop device."

    desktop_user = desktop_device.user

    # Check if the Android device is already registered
    existing_android = Device.objects.filter(device_id=android_device_id).first()
    if existing_android is not None:
        if existing_android.user != desktop_user:
            return None, "Device is already paired with another user account."
        android_device = existing_android
    else:
        # Enforce 1 Desktop + 1 Android per user limit for POC
        user_android = Device.objects.filter(user=desktop_user, device_type=DeviceType.ANDROID).first()
        if user_android:
            user_android.device_id = android_device_id
            user_android.save()
            android_device = user_android
        else:
            android_device = Device.objects.create(
                user=desktop_user,
                device_id=android_device_id,
                device_type=DeviceType.ANDROID,
            )

    # Mark pairing code as used
    pairing_code.is_used = True
    pairing_code.used_at = timezone.now()
    pairing_code.save()

    return android_device, None


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
