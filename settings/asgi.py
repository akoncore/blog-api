"""
ASGI config for settings project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""
#Python modules
import os

#Project modules
from settings.conf import ENV_ID, ENV_POSSIBLE_OPTIONS

assert ENV_ID in ENV_POSSIBLE_OPTIONS, f"Invalid Env ID, Possible options: {ENV_POSSIBLE_OPTIONS}"

os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'settings.env.{ENV_ID}')

#Django modules
from django.core.asgi import get_asgi_application

#Channels modules
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack


def get_websocket_urlpatterns():
    from apps.notifications.routing import websocket_urlpatterns
    return websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                get_websocket_urlpatterns()
            )
        )
    }
)
