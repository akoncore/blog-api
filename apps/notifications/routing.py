#Django 
from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    re_path(
        r"^ws/posts/(?P<post_slug>[-\w]+)/comments/$",
        consumer.CommentConsumer.as_asgi()
    )
]