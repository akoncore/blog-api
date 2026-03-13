import json
from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Listen to Redis Pub/Sub comments channel'

    def handle(self, *args, **options):
        redis_client = cache.client.get_client()
        pubsub = redis_client.pubsub()
        pubsub.subscribe('comments')

        self.stdout.write(
            self.style.SUCCESS('Listening to Redis channel: comments')
        )
        self.stdout.write('Press Ctrl+C to stop\n')

        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        event_data = data.get('data', {})

                        author = (
                            event_data.get('author_name')
                            or event_data.get('author_id', 'Unknown')
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"\n[{data.get('event', 'unknown')}] "
                                f"Comment #{event_data.get('id', '?')} "
                                f"on post '{event_data.get('post_title', '?')}' "
                                f"by {author}"
                            )
                        )
                        self.stdout.write(
                            f"Body: {event_data.get('body', '')}\n"
                        )
                    except json.JSONDecodeError:
                        self.stdout.write(
                            self.style.ERROR('Failed to decode message')
                        )
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nStopped listening.')
            )
            pubsub.unsubscribe('comments')