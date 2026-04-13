import os 

from django.conf import settings

# Celery Configurationq
from celery import Celery
from celery.schedules import crontab
from settings.conf import ENV_ID

os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'settings.env.{ENV_ID}')
app = Celery('blog_api')

app.config_from_object('django.conf:settings',namespace='CELERY')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.beat_schedule = {
    'publish_everyone_every_one_minute':{
        "task":"blog.publish_scheduled_posts",
        "schedule":crontab(minute="*/1")
    },
    'clear-expired-notifications-daily': {
        'task': 'blog.clear_expired_notifications',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'beat'},
    },
    'generate-daily-stats-midnight': {
        'task': 'blog.generate_daily_stats',
        'schedule': crontab(hour=0, minute=0),
        'options': {'queue': 'beat'},
    },
}

app.conf.timezone = 'UTC'
