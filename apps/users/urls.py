from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import UserViewSet,AuthViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='users')
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('users/', include(router.urls)),
    path('auth/', include(router.urls)),
]
