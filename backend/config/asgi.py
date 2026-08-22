"""ASGI config for the Clipboard Sync backend.

Routes HTTP traffic to the standard Django ASGI application and WebSocket
traffic to the clipboard consumer via Django Channels.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from clipboard.routing import websocket_urlpatterns  # noqa: E402

django_asgi_application = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": URLRouter(websocket_urlpatterns),
    }
)