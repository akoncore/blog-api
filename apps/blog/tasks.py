import logging
import json
from datetime import timezone,timedelta

from django.core.cache import cache
from django.conf import settings

from celery import shared_task

from .models import Post 
from .events import _publish_post_event 

logger = logging.getLogger(__name__)

@shared_task(
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


@shared_task(
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

@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries = 3,
    name = 'blog.publish_scheduled_posts'
)
def publish_scheduled_posts(self):
    """
    Check one minute scheduled posts
    """

    now=timezone.now()
    due_post = Post.objects.filter(
        status = Post.Status.SCHEDULED,
        publish_at__lte = now
    ).select_related('author','category')

    published_count = 0
    for post in due_post:
        post.status = Post.Status.PUBLISHED
        post.save(update_fields=(['status'],['updated_at']))
        _publish_post_event(post)
        published_count += 1

    if published_count:
        invalidate_post_cache(post)
        logger.info("publish_scheduled_posts: published %d post(s).", published_count)
    else:
        logger.debug("publish_scheduled_posts: no due posts found.")


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    name = 'blog.clear_expired_notifications',
    max_retries = 3
)
def clear_expired_notifications(self):
    """
    elete notifications older than 30 days. 
    """

    from apps.notifications.model import Notification

    cutoff = timezone.now()-timedelta(days=30)
    deleted_count,_ = Notification.objects.filter(
        created_at__lt = cutoff
    ).delete()


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    name = 'blog.generate_daily_stats',
    max_retries = 3
)
def generate_daily_stats(self):
    """
    Daily stat
    """
    from apps.blog.models import Post,Comment
    from apps.users.models import CustomUser

    since = timezone.now() - timedelta(hours=24)

    post = Post.objects.filter(
        created_at__gte = since
    )
    comment = Post.objects.filter(
        created_at__gte = since
    )
    user = CustomUser.objects.filter(
        data_joined__gte = since
    )
    
    logger.info(
        f"Post stat:{post}, comment stat:{comment}, users stat:{user}"
    )
    
