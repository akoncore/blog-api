import json
import asyncio

from django.core.management.base import BaseCommand

import redis.asyncio as aioredis

from django.conf import settings


# ── helpers ───────────────────────────────────────────────────────────────────

def _redis_url() -> str:
    """
    Resolve the Redis URL from Django settings.
    Supports django-redis CACHES config or a bare REDIS_URL setting.
    """
    try:
        caches = settings.CACHES
        location = caches["default"]["LOCATION"]
        # django-redis location can be a list
        if isinstance(location, (list, tuple)):
            location = location[0]
        return location
    except (AttributeError, KeyError):
        return getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0")


def _format_message(data: dict) -> tuple[str, str]:
    """
    Parse a comment event dict and return (header, body) strings for display.
    """
    event_name = data.get("event", "unknown")
    event_data = data.get("data", {})

    author = (
        event_data.get("author_name")
        or event_data.get("author_id")
        or "Unknown"
    )

    header = (
        f"[{event_name}] "
        f"Comment #{event_data.get('comment_id', '?')} "
        f"on post '{event_data.get('post_title', '?')}' "
        f"by {author} "
        f"(post_id={event_data.get('post_id', '?')})"
    )

    body = f"Body    : {event_data.get('content', '')}"
    timestamp = f"Time    : {event_data.get('created_at', 'N/A')}"

    return header, f"{body}\n  {timestamp}"


# ── async core ────────────────────────────────────────────────────────────────

async def _listen(stdout, style) -> None:
    """
    Main async coroutine.
    """
    url = _redis_url()
    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()


    await pubsub.subscribe("comments")

    stdout.write(style.SUCCESS(f"  ✔  Connected to Redis  : {url}"))
    stdout.write(style.SUCCESS( "  ✔  Subscribed         : comments"))
    stdout.write(            "  Press Ctrl+C to stop\n")

    try:
        # async for keeps the event loop free between messages — no busy-wait.
        async for message in pubsub.listen():

    
            if message.get("type") != "message":
                continue

            raw = message.get("data", "")

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                stdout.write(style.ERROR("  ✘  Failed to decode message — raw data below:"))
                stdout.write(f"     {raw!r}\n")
                continue

            header, details = _format_message(data)
            stdout.write(style.SUCCESS(f"\n  ● {header}"))
            stdout.write(f"  {details}\n")

    except asyncio.CancelledError:
        # Raised when the task is cancelled by KeyboardInterrupt handling below.
        pass

    finally:
        await pubsub.unsubscribe("comments")
        await client.aclose()
        stdout.write(style.WARNING("\n  Stopped listening. Connection closed.\n"))


# ── management command ────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Subscribe to the Redis 'comments' Pub/Sub channel and print "
        "incoming comment events in real time.  Uses async I/O so the "
        "process never blocks a thread while waiting for messages."
    )

    def handle(self, *args, **options) -> None:
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n  Redis Comment Listener\n"))

        try:
            asyncio.run(_listen(self.stdout, self.style))
        except KeyboardInterrupt:
            # asyncio.run() re-raises KeyboardInterrupt after cancelling tasks;
            # we catch it here so Django does not print a traceback.
            pass