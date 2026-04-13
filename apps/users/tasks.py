from logging import getLogger

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation

#Celery
from celery import shared_task


logger = getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    retry_backoff=True,
    default_retry_delay=60,  # Retry after 1 minute
)
def send_welcome_email(
    self,
    user_id,
    lang:str='en',
):

    from apps.users.models import CustomUser

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return
    
    try:
        with translation.override(lang):
            body = render_to_string(
                "emails/welcome/body.html",
                {"first_name": user.first_name, "lang": lang}
            )
            send_mail(
                subject="Welcome to Blog API",
                message="",
                from_email="test@blog.com",
                recipient_list=[user.email],
                html_message=body,
                fail_silently=True
            )
        logger.info(f"Welcome email sent to user {user.email}")

    except Exception as e:
        logger.info(f"Email is not correct:{user.email}")

    

    
    

    

