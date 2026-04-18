"""
Event publishing utilities for blog posts
"""
import json
import logging
from django.core.cache import cache

from .models import Post

logger = logging.getLogger(__name__)


def _publish_post_event(post: Post) -> None:
    """
    Publish a post update event to Redis
    """
    try:
        redis_client = cache.client.get_client()

        event_data = {
            'event': 'post_updated',
            'data': {
                'post_id': post.id,
                'title': post.title,
                'author_id': post.author.id,
                'author_name': post.author.first_name,
                'status': post.status,
            },
            'created_at': post.created_at.isoformat()
        }

        message = json.dumps(event_data, default=str)
        redis_client.publish('posts_feed', message)
        logger.info(f"Published post event for post id: {post.id}")

    except Exception as e:
        logger.error(f"Failed to publish post event: {str(e)}")
