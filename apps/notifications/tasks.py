import logging
import json

from celery import shared_task

logger = logging.getLogger(__name__)

shared_task(
    name ='notification.process_new_comment',
    max_retries = 3,
    retry_backoff=True
)
def process_new_comment(
    comment_id
):
    
    from apps.blog.models import Comment

    try:
        comment = Comment.objects.select_related(
            'post','author', 'post__author'
        ).get(id=comment_id)

    except Comment.DoesNotExist:
        logger.error(f"Comment {comment_id} no")
        return{
            "status":"error"
        }
    
    results = {}

    #Redis Pub/Sub
    results["pubsub"] = _publish_to_redis(comment)

    #Websocket
    results["websocket"] = _send_to_websocket(comment)

    #Send email
    if comment.author != comment.post.author:
        results["email"] = _notify_post_author(comment)
    
    logger.info(f"Comment:{comment} processed: {results}")
    return {
        "status":"ok",
        "comment": comment,
        "results": results
    }


def _publish_to_redis(
        comment
)->str:
    """
    Published comment to redis
    """

    import redis as sync_redis
    from django.conf import settings

    url = settings.CACHES["default"]["LOCATION"]
    if isinstance(url(list, tuple)):
        url = url[0]

    client = sync_redis.from_url(url)

    event_data = {
            'event': 'comment_published',
            'data': {
                'comment_id': comment.id,
                'post_id': comment.post.id,
                'post_title': comment.post.title,
                'author_id': comment.author.id,
                'author_name': comment.author.first_name,
                'content': comment.body,
                'created_at': comment.created_at.isoformat()
            }
        }
    client.publish("comments",json.dumps(event_data,default=str))
    client.close()

    return "published"


def _send_to_websocket(comment):
    """
    Send comment 
    """
    #channels
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    

    layer = get_channel_layer()
    group_name = f'post_{comment}_comments'

    async_to_sync(layer.group_send)(
            group_name,
            {
                "type": "comment.message",
                "data": {
                    "comment_id": comment.id,
                    "author": {
                        "id":    comment.author.id,
                        "email": comment.author.email,
                    },
                    "body":       comment.body,
                    "created_at": comment.created_at.isoformat(),
                }
            }
        )
    return "send"

def _notify_post_author(comment):
    """
    Send email
    """
    from django.core.mail import send_mail

    send_mail(
            subject=f"Жаңа коммент: {comment.post.title}",
            message=(
                f"{comment.author.first_name} коммент жазды:\n\n"
                f"{comment.body}"
            ),
            from_email="noreply@blog.com",
            recipient_list=[comment.post.author.email],
            fail_silently=True,
        )
    return "Send email"
    