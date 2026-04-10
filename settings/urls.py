"""
URL configuration for settings project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)
from apps.blog.views_async import StasView
from apps.notifications.see_view import post_stream



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include("apps.users.urls")),
    path('api/', include("apps.blog.urls")),
    path('__debug__/', include('debug_toolbar.urls')),
    path('api/stats/',StasView.as_view(),name='stats'),

    path('api/posts/stream/', post_stream, name='post_stream'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    path('api/docs/', SpectacularSwaggerView.as_view(),name='swagger'),
    path('api/redoc/',SpectacularRedocView.as_view(),name='redoc'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema')
    
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)