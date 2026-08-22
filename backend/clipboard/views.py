from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from clipboard.models import ClipboardEntry
from clipboard.serializers import ClipboardEntrySerializer


class ClipboardEntryCreateView(APIView):
    """Create a development clipboard entry from a text payload."""

    def post(self, request: Request) -> Response:
        serializer = ClipboardEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(ClipboardEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class LatestClipboardEntryView(APIView):
    """Return the most recently created clipboard entry."""

    def get(self, request: Request) -> Response:
        entry = ClipboardEntry.objects.first()
        if entry is None:
            return Response(
                {"detail": "No clipboard entries found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ClipboardEntrySerializer(entry).data)
