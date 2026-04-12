import logging

from django.core.cache import cache
from django.conf import settings

from celery import shared_task

logger = logging.getLogger(__name__)

shared_task(
    name = 'blog.invalidate_post_cache',
    max_retries = 1,
    retry_backoff=True
)
def invalidate_post_cache()->dict:
    """
    Invalidated posts caches
    """
    deleted_keys = []

    for lang in settings.SUPPORTED_LANGUAGES:
        key = f"Published_post_{lang}"
        cache.delete(key)
        deleted_keys.append(key)
        logger.info(f"Cache deleted: {key}")

    logger.info(f"invalidated post cache {deleted_keys}")
    return deleted_keys


shared_task(
    name = 'blog.posts_create_update',
    max_retries = 1,
    retry_backoff=True
)
def posts_create_update(    
    lang: str = 'en'
)->dict:
    
    from apps.blog.models import Post
    from apps.blog.serializers import PostSerializer

    try:
        queryset = Post.objects.filter(
            status = Post.Status.PUBLISHED
        ).select_related('author','category').prefetch_related('tags')

        serializer = PostSerializer(
            queryset,
            many = True
        )
        key = f"Published_post_{key}"
        cache.set(key, serializer.data, timeout=60)

        logger.info(f"Cache wwarmed for lang {lang}: {queryset.conut()} posts")
        return {
            "status":"ok",
            "lang":lang,
            "count":queryset.conut()
        }
    
    except Exception as e:
        logger.error(f"Error:{e}")
        return{
            "status":"error",
            "error": e
        }

