from logging import getLogger
from typing import Any
import pytz

#Django imports
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.utils import translation
from django.core.mail import send_mail
from django.template.loader import render_to_string

#Python imports
from rest_framework.response import Response
from rest_framework.request import Request 
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.status import (
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST, 
    HTTP_205_RESET_CONTENT,
    HTTP_200_OK, 
    HTTP_404_NOT_FOUND, 
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_401_UNAUTHORIZED, 
    HTTP_403_FORBIDDEN,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

from .serializers import (
    RegisterSerializer, UserProfileSerializer, LoginSerializer,
    UpdateUserProfileSerializer, ChangePasswordSerializer,
)
from .models import CustomUser
from .permissions import IsOwnerOrReadOnly

logger = getLogger(__name__)


def is_rate_limited(request, action_name, limit) -> bool:
    ip = request.META.get('REMOTE_ADDR')
    cache_key = 'rate_limit_%s_%s' % (action_name, ip)
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    cache.set(cache_key, count + 1, timeout=60)
    return False


def rate_limit_handler(request: Any, exception: Any) -> Response:
    logger.warning(
        'Rate limit exceeded for user: %s from IP: %s',
        request.user.id if request.user.is_authenticated else 'Anonymous',
        request.META.get('REMOTE_ADDR')
    )
    return Response(
        {'detail': _('Too many requests. Please try again later.')},
        status=HTTP_429_TOO_MANY_REQUESTS
    )


@extend_schema_view(
    register=extend_schema(
        summary='Register a new user',
        description='Registers a new user and sends welcome email',
        tags=['Authentication'],
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(response=UserProfileSerializer, description='User registered successfully'),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required'),
            429: OpenApiResponse(description='Rate limit exceeded'),
        }
    ),
    login=extend_schema(
        summary='Login a user',
        description='Authenticate user and return access and refresh tokens',
        tags=['Authentication'],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(response=UserProfileSerializer, description='User logged in successfully'),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required'),
            429: OpenApiResponse(description='Rate limit exceeded'),
        }
    ),
    logout=extend_schema(
        summary='Logout a user',
        description='Blacklist refresh token to logout user',
        tags=['Authentication'],
        responses={
            205: OpenApiResponse(description='User logged out successfully'),
            400: OpenApiResponse(description='Refresh token required or invalid'),
            401: OpenApiResponse(description='Authentication required'),
        }
    ),
    refresh_token=extend_schema(
        summary='Refresh access token',
        description='Obtain new access token using refresh token',
        tags=['Authentication'],
        request=None,
        responses={
            200: OpenApiResponse(description='Access token refreshed successfully'),
            400: OpenApiResponse(description='Token refresh failed'),
        }
    ),
    set_language=extend_schema(
        summary='Set preferred language',
        description='Authenticated user can update preferred language',
        tags=['Authentication'],
        request=None,
        responses={
            200: OpenApiResponse(description='Language updated successfully'),
            400: OpenApiResponse(description='Invalid language'),
            401: OpenApiResponse(description='Authentication required'),
        }
    ),
    set_timezone=extend_schema(
        summary='Set user timezone',
        description='Authenticated user can update timezone',
        tags=['Authentication'],
        request=None,
        responses={
            200: OpenApiResponse(description='Timezone updated successfully'),
            400: OpenApiResponse(description='Invalid timezone'),
            401: OpenApiResponse(description='Authentication required'),
        }
    ),
)


class AuthViewSet(ViewSet):

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request) -> Response:
        if is_rate_limited(request, 'register', 10):
            return rate_limit_handler(request, None)

        email = request.data.get('email')
        serializer = RegisterSerializer(data=request.data)
        logger.info('Registering user with email: %s', email)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            user_lang = request.data.get("language", "en")
            if user_lang not in ["en", "kk", "ru"]:
                user_lang = "en"

            with translation.override(user_lang):
                body = render_to_string(
                    "emails/welcome/body.html",
                    {"full_name": user.full_name, "lang": user_lang}
                )
                send_mail(
                    subject="Welcome to Blog API",
                    message="",
                    from_email="test@blog.com",
                    recipient_list=[user.email],
                    html_message=body,
                    fail_silently=True
                )

            logger.info('User registered successfully: %s', user.email)

            return Response(
                {
                    'message': _('User registered successfully'),
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                },
                status=HTTP_201_CREATED
            )

        logger.warning('Registration failed for email: %s, errors: %s', email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request) -> Response:
        if is_rate_limited(request, 'login', 5):
            return rate_limit_handler(request, None)

        email = request.data.get('email')
        serializer = LoginSerializer(data=request.data, context={'request': request})
        logger.info('Login attempt for email: %s', email)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info('User logged in successfully: %s', user.email)
            return Response(
                {
                    'message': _('User logged in successfully'),
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                },
                status=HTTP_200_OK
            )

        logger.warning('Login failed for email: %s, errors: %s', email, serializer.errors)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action( 
        methods=("PATCH",), 
        detail=False, 
        url_path="language", 
        url_name="language", 
        permission_classes=(IsAuthenticated,), 
    ) 
    def set_language( 
        self, 
        request: Request, 
        *args, 
        **kwargs, 
    ) -> Response: 
        """PATCH /api/auth/language — сохранить язык пользователя""" 
        from django.conf import settings 

        lang = request.data.get("language") 

        if lang not in settings.SUPPORTED_LANGUAGES: 
            return Response( 
                {"detail": _("Invalid language. Choose from: en, ru, kk")}, 
                status=HTTP_400_BAD_REQUEST, 
            ) 

        request.user.preferred_language = lang 
        request.user.save(update_fields=["preferred_language"]) 

        logger.info(f"Language updated: user_id={request.user.id}, lang={lang}") 
        return Response( 
            {"detail": _("Language updated successfully."), "language": lang}, 
            status=HTTP_200_OK, 
        )

    @action( 
        methods=("PATCH",), 
        detail=False, 
        url_path="timezone", 
        url_name="timezone", 
        permission_classes=(IsAuthenticated,), 
    ) 
    def set_timezone( 
        self, 
        request: Request, 
        *args, 
        **kwargs, 
    ) -> Response: 
        """PATCH /api/auth/timezone — сохранить часовой пояс пользователя""" 
        tz_name = request.data.get("timezone") 

        if not tz_name: 
            return Response( 
                {"detail": _("Invalid timezone")}, 
                status=HTTP_400_BAD_REQUEST, 
            ) 
        try: 
            pytz.timezone(tz_name) 
        except pytz.exceptions.UnknownTimeZoneError: 
            return Response( 
                {"detail": _("Invalid timezone")}, 
                status=HTTP_400_BAD_REQUEST, 
            ) 

        request.user.timezone = tz_name 
        request.user.save(update_fields=["timezone"]) 

        logger.info(f"Timezone updated: user_id={request.user.id}, timezone={tz_name}") 
        return Response( 
            {"detail": _("Timezone updated successfully."), "timezone": tz_name}, 
            status=HTTP_200_OK, 
        )

    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request) -> Response:
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': _('Refresh token required')}, 
                status=HTTP_400_BAD_REQUEST
            )
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            user_info = request.user.email if request.user.is_authenticated else 'anonymous'
            logger.info('User logged out: %s', user_info)
            return Response(
                {'message': _('User logged out successfully')}, 
                status=HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            logger.error('Logout failed: %s', str(e))
            return Response({'error': _('Logout failed')}, status=HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='refresh-token')
    def refresh_token(self, request) -> Response:
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)}, status=HTTP_200_OK)
        except Exception as e:
            logger.error('Token refresh failed: %s', str(e))
            return Response({'error': _('Token refresh failed')}, status=HTTP_400_BAD_REQUEST)


class UserViewSet(ViewSet):

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['update_profile', 'change_password', 'destroy']:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def retrieve(self, request, pk=None) -> Response:
        try:
            user = CustomUser.objects.get(pk=pk)
            return Response(UserProfileSerializer(user).data, status=HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error': _('User not found')}, status=HTTP_404_NOT_FOUND)

    def list(self, request) -> Response:
        users = CustomUser.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(
            {'users': serializer.data, 'total_users': users.count()},
            status=HTTP_200_OK
        )

    def destroy(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response({'error': _('Authentication required')}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': _('User not found')}, status=HTTP_404_NOT_FOUND)

        if user != request.user and not request.user.is_superuser:
            return Response(
                {'error': _('You do not have permission to delete this account')},
                status=HTTP_403_FORBIDDEN
            )

        user.delete()
        logger.info('User deleted: %s', pk)
        return Response({'message': _('User deleted successfully')}, status=HTTP_205_RESET_CONTENT)

    @action(detail=True, methods=['patch'], url_path='update-profile')
    def update_profile(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response({'error': _('Authentication required')}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': _('User not found')}, status=HTTP_404_NOT_FOUND)

        if user != request.user and not request.user.is_superuser:
            return Response(
                {'error': _('You do not have permission to update this profile')},
                status=HTTP_403_FORBIDDEN
            )

        serializer = UpdateUserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': _('Profile updated successfully'), 'user': UserProfileSerializer(user).data}
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response({'error': _('Authentication required')}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': _('User not found')}, status=HTTP_404_NOT_FOUND)

        if user != request.user:
            return Response(
                {'error': _('You do not have permission to change this password')},
                status=HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            logger.info('Password changed for user: %s', pk)
            return Response({'message': _('Password changed successfully')}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)