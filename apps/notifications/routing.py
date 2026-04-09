#Django 
from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    re_path(
        r'ws://<host>/posts/<slug>/comments/',
        consumer.CommentConsumer.as_asgi()
    )
]