#django imports
from django.urls import path, include

#rest framework imports
from rest_framework.routers import DefaultRouter

#project imports
from apps.notifications.view import NotificationViewSet

router = DefaultRouter()

router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
