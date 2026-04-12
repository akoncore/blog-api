from decouple import config



#-----------------------------
#ENV_ID
#
ENV_POSSIBLE_OPTIONS = (
    "local",
    "prod"
)
ENV_ID = config("BLOG_ENV_ID",cast=str)
SECRET_KEY = config('BLOG_SECRET_KEY', default='your-secret-key')
CELERY_BROKER_URL = config('BLOG_CELERY_BROKER_URL', default='redis://localhost:6379/1')


