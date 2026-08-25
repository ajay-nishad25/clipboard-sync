from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.models import User
from clipboard.models import ClipboardEntry
from clipboard.serializers import ClipboardEntrySerializer, ClipboardStateSerializer
from clipboard.services import (
    get_active_user_clipboard,
    resolve_device_and_user,
    set_user_clipboard,
)


class ClipboardEntryCreateView(APIView):
    """Create a clipboard entry and update the user's active ClipboardState."""

    def post(self, request: Request) -> Response:
        serializer = ClipboardEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        content = serializer.validated_data["content"]

        device, user = resolve_device_and_user(device_id)
        if user:
            set_user_clipboard(user, content)

        entry = serializer.save()
        return Response(ClipboardEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class LatestClipboardEntryView(APIView):
    """Return the user-scoped active ClipboardState if not expired."""

    def get(self, request: Request) -> Response:
        device_id = request.query_params.get("device_id")
        user = None

        if device_id:
            _, user = resolve_device_and_user(device_id)
        else:
            # Fallback for development/tests where device_id is omitted
            user = User.objects.first()

        if user is None:
            return Response(
                {"detail": "No clipboard entries found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        state = get_active_user_clipboard(user)
        if state is None:
            return Response(
                {"detail": "No clipboard entries found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Structure response with content and timestamps, compatible with existing API format
        response_data = {
            "id": state.id,
            "device_id": device_id or (user.devices.first().device_id if user.devices.exists() else "unknown"),
            "content": state.content,
            "updated_at": state.updated_at,
            "expires_at": state.expires_at,
        }
        return Response(response_data, status=status.HTTP_200_OK)
