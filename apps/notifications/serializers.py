#Rest modules 
from rest_framework.serializers import (
    ModelSerializer,
    Serializer,
    CharField,
    IntegerField
)

#Project modules
from apps.notifications.model import Notification


class NotificationSerializer(ModelSerializer):
    comment = CharField(source="comment.content",read_only=True)
    author = CharField(source="comment.author.first_name",read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "comment",
            "author",
            "is_read",
            "created_at"
        ]

class UnreadNotificationCountSerializer(Serializer):
    unread_count = IntegerField(min_value=0)
    
