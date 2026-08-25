from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User
from clipboard.models import ClipboardEntry, DeviceCredential, DeviceType
from clipboard.serializers import (
    ClipboardEntrySerializer,
    ClipboardStateSerializer,
    DeviceCredentialRegisterSerializer,
    DevicePairSerializer,
    PairingCodeCreateSerializer,
)
from clipboard.services import (
    authenticate_device_token,
    create_pairing_code,
    get_active_user_clipboard,
    issue_device_credential,
    pair_android_device,
    resolve_device_and_user,
    revoke_device_credential,
    set_user_clipboard,
)


def extract_bearer_token(request: Request) -> str | None:
    """Extract raw authentication token from Authorization header or query parameter."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    token_param = request.query_params.get("token")
    if token_param and token_param.strip():
        return token_param.strip()

    # Development fallback query param
    device_id_param = request.query_params.get("device_id")
    if device_id_param and device_id_param.strip():
        return device_id_param.strip()

    return None


class DeviceCredentialRegisterView(APIView):
    """Register or obtain an authentication credential for a desktop device."""

    def post(self, request: Request) -> Response:
        serializer = DeviceCredentialRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        device, user = resolve_device_and_user(device_id, default_type=DeviceType.DESKTOP)

        if not device:
            return Response({"detail": "Invalid device ID."}, status=status.HTTP_400_BAD_REQUEST)

        _, raw_token = issue_device_credential(device)
        return Response(
            {
                "device_id": device.device_id,
                "credential": raw_token,
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceUnpairView(APIView):
    """Revoke the caller's device credential and unpair device."""

    def post(self, request: Request) -> Response:
        token = extract_bearer_token(request)
        if not token:
            body_token = request.data.get("token") if isinstance(request.data, dict) else None
            token = body_token if isinstance(body_token, str) else None

        cred, device, user = authenticate_device_token(token) if token else (None, None, None)
        if not cred:
            return Response(
                {"detail": "Invalid or revoked device credential."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        revoke_device_credential(cred)
        return Response(
            {"status": "unpaired", "detail": "Device credential revoked successfully."},
            status=status.HTTP_200_OK,
        )


class ClipboardEntryCreateView(APIView):
    """Create a clipboard entry and update the user's active ClipboardState."""

    def post(self, request: Request) -> Response:
        serializer = ClipboardEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        content = serializer.validated_data["content"]

        token = extract_bearer_token(request) or device_id
        cred, device, user = authenticate_device_token(token)

        if not cred or not user:
            return Response(
                {"detail": "Invalid or revoked device credential."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        set_user_clipboard(user, content)
        entry = serializer.save()
        return Response(ClipboardEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class LatestClipboardEntryView(APIView):
    """Return the authenticated user-scoped active ClipboardState if not expired."""

    def get(self, request: Request) -> Response:
        token = extract_bearer_token(request)
        cred, device, user = authenticate_device_token(token) if token else (None, None, None)

        if not cred or not user or not device:
            return Response(
                {"detail": "Invalid or revoked device credential."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        state = get_active_user_clipboard(user)
        if state is None:
            return Response(
                {"detail": "No clipboard entries found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = {
            "id": state.id,
            "device_id": device.device_id,
            "content": state.content,
            "updated_at": state.updated_at,
            "expires_at": state.expires_at,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class PairingCodeCreateView(APIView):
    """Generate a temporary pairing code for a desktop device."""

    def post(self, request: Request) -> Response:
        serializer = PairingCodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        device, user = resolve_device_and_user(device_id, default_type=DeviceType.DESKTOP)

        if not device or device.device_type != DeviceType.DESKTOP:
            return Response(
                {"detail": "Pairing codes can only be generated by desktop devices."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pairing_code = create_pairing_code(device)
        return Response(
            {
                "code": pairing_code.code,
                "expires_at": pairing_code.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class DevicePairView(APIView):
    """Pair an Android device with a desktop device using a pairing code."""

    def post(self, request: Request) -> Response:
        serializer = DevicePairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code_str = serializer.validated_data["code"]
        android_device_id = serializer.validated_data["android_device_id"]

        android_device, raw_token, error = pair_android_device(code_str, android_device_id)
        if error:
            if "already paired with another user" in error:
                return Response({"detail": error}, status=status.HTTP_409_CONFLICT)
            elif "expired" in error or "used" in error or "required" in error or "desktop device" in error:
                return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": error}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "status": "paired",
                "device_id": android_device.device_id,
                "credential": raw_token,
                "user_id": android_device.user.id,
                "user_name": android_device.user.username,
            },
            status=status.HTTP_200_OK,
        )
