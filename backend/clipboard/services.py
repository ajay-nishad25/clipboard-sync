from __future__ import annotations

import secrets
import string
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from clipboard.models import ClipboardState, Device, DeviceCredential, DeviceType, PairingCode

# Alphabet excluding visually ambiguous characters: 0, O, 1, I, L
_PAIRING_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_device_token() -> str:
    """Generate a cryptographically secure opaque token string."""
    return f"devtok_{secrets.token_hex(16)}"


def issue_device_credential(device: Device) -> tuple[DeviceCredential, str]:
    """Issue a new DeviceCredential for *device* and return (credential_obj, raw_token)."""
    raw_token = generate_device_token()
    token_hash = DeviceCredential.hash_token(raw_token)
    credential = DeviceCredential.objects.create(
        device=device,
        token_hash=token_hash,
    )
    return credential, raw_token


def authenticate_device_token(raw_token: str) -> tuple[DeviceCredential | None, Device | None, User | None]:
    """Authenticate a raw token string.

    Returns (credential, device, user) if valid and active, or (None, None, None) if invalid or revoked.
    """
    if not raw_token or not isinstance(raw_token, str) or not raw_token.strip():
        return None, None, None

    raw_token = raw_token.strip()
    token_hash = DeviceCredential.hash_token(raw_token)

    try:
        cred = DeviceCredential.objects.select_related("device__user").get(token_hash=token_hash)
        if cred.revoked_at is not None:
            return None, None, None

        cred.last_used_at = timezone.now()
        cred.save(update_fields=["last_used_at"])
        return cred, cred.device, cred.device.user
    except DeviceCredential.DoesNotExist:
        # Development fallback mode (Section 17):
        # Auto-provision credentials for legacy dev IDs (e.g. desktop-001 or android-001)
        if raw_token.startswith("desktop-") or raw_token.startswith("android-"):
            device, user = resolve_device_and_user(raw_token)
            if device:
                cred, _ = DeviceCredential.objects.get_or_create(
                    device=device,
                    token_hash=token_hash,
                    defaults={"last_used_at": timezone.now()},
                )
                if cred.revoked_at is not None:
                    return None, None, None
                return cred, device, user
        return None, None, None


def revoke_device_credential(credential: DeviceCredential) -> None:
    """Revoke a DeviceCredential."""
    credential.revoked_at = timezone.now()
    credential.save(update_fields=["revoked_at"])


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


def pair_android_device(code_str: str, android_device_id: str) -> tuple[Device | None, str | None, str | None]:
    """Pair an Android device using a pairing code.

    Returns (android_device, raw_token, None) on success, or (None, None, error_message) on failure.
    """
    if not code_str or not isinstance(code_str, str) or not code_str.strip():
        return None, None, "Pairing code is required."

    if not android_device_id or not isinstance(android_device_id, str) or not android_device_id.strip():
        return None, None, "Android device ID is required."

    normalized_code = code_str.strip().upper()
    if len(normalized_code) == 8 and "-" not in normalized_code:
        normalized_code = f"{normalized_code[:4]}-{normalized_code[4:]}"

    try:
        pairing_code = PairingCode.objects.select_related("desktop_device__user").get(code=normalized_code)
    except PairingCode.DoesNotExist:
        return None, None, "Invalid or unknown pairing code."

    if pairing_code.is_used:
        return None, None, "Pairing code has already been used."

    if timezone.now() >= pairing_code.expires_at:
        return None, None, "Pairing code has expired."

    desktop_device = pairing_code.desktop_device
    if desktop_device.device_type != DeviceType.DESKTOP:
        return None, None, "Pairing code does not belong to a desktop device."

    desktop_user = desktop_device.user

    # Check if the Android device is already registered
    existing_android = Device.objects.filter(device_id=android_device_id).first()
    if existing_android is not None:
        if existing_android.user != desktop_user:
            return None, None, "Device is already paired with another user account."
        android_device = existing_android
    else:
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

    # Issue device credential for Android device
    _, raw_token = issue_device_credential(android_device)

    # Mark pairing code as used
    pairing_code.is_used = True
    pairing_code.used_at = timezone.now()
    pairing_code.save()

    return android_device, raw_token, None


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
