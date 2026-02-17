#Python imports
from logging import getLogger
from typing import Any, Dict

#Django imports
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache

#REST Framework imports
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_205_RESET_CONTENT,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny

#Project imports
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    LoginSerializer,
    UpdateUserProfileSerializer,
    ChangePasswordSerializer
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
        {
            'detail': 'Too many requests. Please try again later.'
        },
        status=HTTP_429_TOO_MANY_REQUESTS   
    )


class AuthViewSet(ViewSet):
    """
    Register View Set
    """

    @action(detail=False,methods=['post'],url_path='register')
    def register(self,request)->Response:
        """
        Register a new user
        """
        if is_rate_limited(request, 'register',10):
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
                    'user':UserProfileSerializer(user).data,
                    'tokens':{
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                },
                status=HTTP_201_CREATED
            )
        
        logger.warning(
            'Registration failed for email: %s, errors: %s', 
            email, 
            serializer.errors
        )
        return Response(
            serializer.errors,
            status=HTTP_400_BAD_REQUEST
        )
    


    @action(detail=False,methods=['post'],url_path='login')
    def login(self,request)->Response:
        """
        Login a user
        """
        if is_rate_limited(request, 'login', 5):
            return rate_limit_handler(request, None)
        

        email = request.data.get('email')
        serializer = LoginSerializer(
            data=request.data, 
            context={
                'request': request
            }
        )

        logger.info('Login attempt for email: %s', email)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info('User logged in successfully: %s', user.email)
            return Response(
                {
                    'message': 'User logged in successfully',
                    'user':UserProfileSerializer(user).data,
                    'tokens':{
                        'access': str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                },
                status=HTTP_200_OK
            )
        
        logger.warning(
            'Login failed for email: %s, errors: %s', 
            email, 
            serializer.errors
        )
        return Response(
            serializer.errors,
            status=HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self,request)->Response:
        """
        Logout a user
        """
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(
                'User logged out successfully: %s', 
                request.user.email
            )

            return Response(
                {'message': 'User logged out successfully'},
                status=HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            logger.error(
                'Logout failed for user: %s, error: %s', 
                request.user.email, 
                str(e)
            )
            return Response(
                {'error': 'Logout failed'},
                status=HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='refresh-token')
    def refresh_token(self,request)->Response:
        """
        Refresh access token
        """
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)

            logger.info(
                'Access token refreshed successfully for user: %s', 
                request.user.email
            )

            return Response(
                {'access': new_access_token},
                status=HTTP_200_OK
            )
        except Exception as e:
            logger.error(
                'Token refresh failed for user: %s, error: %s', 
                request.user.email, 
                str(e)
            )
            return Response(
                {'error': 'Token refresh failed'},
                status=HTTP_400_BAD_REQUEST
            )
        

class UserViewSet(ViewSet):
    """
    User View Set
    """

    def get_permissions(self):
        
        if self.action in ['list','retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['update_profile','change_password','destroy']:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def retrieve(self,request,pk=None)->Response:
        """
        Get user profile
        """
        try:
            user = CustomUser.objects.get(pk=pk)
            serializer = UserProfileSerializer(user)
            logger.info('User profile retrieved successfully: %s', user.pk)
            return Response(
                serializer.data,
                status=HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            logger.warning('User not found with id: %s', pk)
            return Response(
                {
                    'error': 'User not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
    def list(self,request)->Response:
        """
        List all users
        """
        users = CustomUser.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        logger.info('User list retrieved successfully, total users: %d', users.count())

        if not users.exists():
            logger.warning('No users found in the database')
            return Response(
                {
                    'message': 'No users found'
                },
                status=HTTP_200_OK
            )

        return Response(
            {
                'users': serializer.data,
                'total_users': users.count()
            },
            status=HTTP_200_OK
        )
    
    def destroy(self,request,pk=None)->Response:
        """
        Delete a user
        """
        try:
            user = CustomUser.objects.get(pk=pk)
            user.delete()
            logger.info('User deleted successfully: %s', pk)
            return Response(
                {
                    'message': 'User deleted successfully'
                },
                status=HTTP_205_RESET_CONTENT
            )
        except CustomUser.DoesNotExist:
            logger.warning('User not found for deletion with id: %s', pk)
            return Response(
                {
                    'error': 'User not found'
                },
                status=HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'], url_path='update-profile')
    def update_profile(self,request,pk=None)->Response:
        """
        Update user profile
        """
        try:
            user = CustomUser.objects.get(pk=pk)
            serializer = UpdateUserProfileSerializer(
                user, 
                data=request.data, 
                partial=True
            )

            logger.info('Updating profile for user: %s', pk)

            if serializer.is_valid():
                serializer.save()
                logger.info('User profile updated successfully: %s', pk)
                return Response(serializer.data)
            
            logger.warning(
                'Profile update failed for user: %s, errors: %s', 
                pk, 
                serializer.errors
            )
            return Response(
                serializer.errors,
                status=HTTP_400_BAD_REQUEST
            )
        except CustomUser.DoesNotExist:
            logger.warning('User not found for profile update with id: %s', pk)
            return Response(
                {
                    'error': 'User not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self,request,pk=None)->Response:
        """Change user password"""
        try:
            user = CustomUser.objects.get(pk=pk)
            serializer = ChangePasswordSerializer(
                data = request.data,
                context={
                    'request': request
                }
            )
            logger.info('Changing password for user: %s', pk)

            if serializer.is_valid():
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                logger.info('Password changed successfully for user: %s', pk)
                return Response(
                    {
                        'message': 'Password changed successfully'
                    },
                    status=HTTP_200_OK
                )
            logger.warning(
                'Password change failed for user: %s, errors: %s', 
                pk, 
                serializer.errors
            )
            return Response(
                serializer.errors,
                status=HTTP_400_BAD_REQUEST
            )
        except CustomUser.DoesNotExist:
            logger.warning('User not found for password change with id: %s', pk)
            return Response(
                {
                    'error': 'User not found'
                },
                status=HTTP_404_NOT_FOUND
            )
