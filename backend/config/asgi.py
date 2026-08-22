# """ASGI config for the Clipboard Sync backend."""

# import os

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.core.asgi import get_asgi_application

# from clipboard.routing import websocket_urlpatterns

# django_asgi_application = get_asgi_application()

# application = ProtocolTypeRouter(
#     {
#         "http": django_asgi_application,
#         "websocket": URLRouter(websocket_urlpatterns),
#     }
# )


"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()