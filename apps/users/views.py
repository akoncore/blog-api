from logging import getLogger
from typing import Any

from django.core.cache import cache
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.status import (
    HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_205_RESET_CONTENT,
    HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_429_TOO_MANY_REQUESTS,
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import (
    RegisterSerializer, UserProfileSerializer, LoginSerializer,
    UpdateUserProfileSerializer, ChangePasswordSerializer
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
        {'detail': 'Too many requests. Please try again later.'},
        status=HTTP_429_TOO_MANY_REQUESTS
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
            logger.info('User registered successfully: %s', user.email)
            return Response(
                {
                    'message': 'User registered successfully',
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
                    'message': 'User logged in successfully',
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

    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request) -> Response:
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info('User logged out: %s', request.user.email)
            return Response({'message': 'User logged out successfully'}, status=HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error('Logout failed: %s', str(e))
            return Response({'error': 'Logout failed'}, status=HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='refresh-token')
    def refresh_token(self, request) -> Response:
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)}, status=HTTP_200_OK)
        except Exception as e:
            logger.error('Token refresh failed: %s', str(e))
            return Response({'error': 'Token refresh failed'}, status=HTTP_400_BAD_REQUEST)


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
            return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)

    def list(self, request) -> Response:
        users = CustomUser.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(
            {'users': serializer.data, 'total_users': users.count()},
            status=HTTP_200_OK
        )

    def destroy(self, request, pk=None) -> Response:
        
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)

        # Тек өзін немесе superuser өшіре алады
        if user != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'You do not have permission to delete this account'},
                status=HTTP_403_FORBIDDEN
            )

        user.delete()
        logger.info('User deleted: %s', pk)
        return Response({'message': 'User deleted successfully'}, status=HTTP_205_RESET_CONTENT)

    @action(detail=True, methods=['patch'], url_path='update-profile')
    def update_profile(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)

        # Тек өз профилін жаңарта алады
        if user != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'You do not have permission to update this profile'},
                status=HTTP_403_FORBIDDEN
            )

        serializer = UpdateUserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Profile updated successfully', 'user': UserProfileSerializer(user).data}
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=HTTP_401_UNAUTHORIZED)

        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=HTTP_404_NOT_FOUND)

        # Тек өз паролін өзгерте алады
        if user != request.user:
            return Response(
                {'error': 'You do not have permission to change this password'},
                status=HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            logger.info('Password changed for user: %s', pk)
            return Response({'message': 'Password changed successfully'}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)