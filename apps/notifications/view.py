from rest_framework.viewsets import ViewSet
from rest_framework.response import Response as DRFResponse
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated  
from rest_framework.status import(
    HTTP_200_OK
) 
from rest_framework.permissions import IsAuthenticated

from apps.notifications.model import Notification
from apps.notifications.serializers import (
    NotificationSerializer,
    UnreadNotificationCountSerializer
)


class NotificationViewSet(ViewSet):
    """
    polling viewset for notifications
    """
    permission_classes = [IsAuthenticated]

    def list(self,request):
        """
        List notifications for the authenticated user.
        """
        queryset = self.get_queryset()
        serializer = NotificationSerializer(queryset, many=True)
        return DRFResponse(serializer.data)

    def get_queryset(self):
        user = Notification.objects.filter(
            recipient=self.request.user
        ).select_related("comment","comment__author").order_by("-created_at")
        return user
    
    @action(
        detail=False,
        methods=["get"],
        url_path="count",
    )
    def count(self,request):
        """
        Count unread notifications for the authenticated user.
        """
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        serializer = UnreadNotificationCountSerializer(
            {"unread_count": count}
        )
        return DRFResponse(
            serializer.data, 
            status=HTTP_200_OK
        )
    
    @action(
        detail=True,
        methods=["post"],
        url_path="read",
    )
    def mark_as_read(self,request):
        """
        Read a notification and mark it as read.
        """
        unread_notification = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        
        serializer = NotificationSerializer(
            {
                'updated_notifications': unread_notification
            },
            many=True
        )
        return DRFResponse(
            serializer.data, 
            status=HTTP_200_OK
        )