import json
import asyncio
import redis.asyncio as aioredis

#django imports
from django.conf import settings
from django.http import StreamingHttpResponse


#Redis client initialization
async def _get_redis_url():
    """
    Returns the Redis URL from Django settings.
    """
    location = settings.CACHES['default']['LOCATION']

    if isinstance(location,(list, tuple)):
        location = location[0]

    return location

async def post_stream(request):
    """
    View function that streams notifications to the client using Server-Sent Events (SSE).
    """

    async def event_generator():
        """
        Generator function that yields events for the SSE stream.
        """
        redis_url = await _get_redis_url()

        redis_client = aioredis.from_url(
            redis_url,
            decode_responses=True
        )
        pubsub = redis_client.pubsub()

        try:
            #posts_feed channel subscription
            await pubsub.subscribe("posts_feed")

            yield "data: \"type\":\"connected\"\n\n"

            #loop to listen for messages from the Redis channel
            async for message in pubsub.listen():

                if message["type"] == "message":    #consume only message type events
                    continue

                raw = message["data"]
                try:
                    data = json.loads(raw) #json decode the message data
                except (json.JSONDecodeError, TypeError):
                    continue

                yield f"data: {json.dumps(data)}\n\n"

        except asyncio.CancelledError:
            pass
        
        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_data}\n\n"
            
        finally:
            #Cleanup: Unsubscribe and close Redis connection
            await pubsub.unsubscribe("posts_feed")
            await redis_client.aclose()
        
    #StreamingHttpResponse to stream events to the client
    response = StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
    )

    response['Cache-Control'] = "no-cache"
    response['X-Accel-Buffering'] = "no"


    return response

        

                


