from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.blog.views import post_stream
from .views import PostViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='posts')
router.register(r'comments', CommentViewSet, basename='comments')

urlpatterns = [
    path('', include(router.urls)),
    path('api/posts/stream/', post_stream, name='post_stream'),
]