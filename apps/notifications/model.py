from django.db.models import (
    Model,
    ForeignKey,
    CASCADE,
    BooleanField,
    DateTimeField
)
from django.conf import settings

from apps.blog.models import Comment



class Notification(Model):
    """
    Model representing a notification.
    """
    recipient = settings.AUTH_USER_MODEL

    comment = ForeignKey(
        Comment,
        on_delete=CASCADE,
        related_name="notifications"
    )
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient} - Comment: {self.comment}"

