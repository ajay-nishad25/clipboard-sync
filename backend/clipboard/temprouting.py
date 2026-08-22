"""WebSocket routes for the clipboard application."""

from django.urls import path

from clipboard.consumers import ClipboardConsumer

websocket_urlpatterns = [
    path("ws/clipboard/", ClipboardConsumer.as_asgi()),
]
