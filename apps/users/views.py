#Python imports
from logging import getLogger

#Django imports
from django.decorators import ratelimit

#REST Framework imports
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_205_RESET_CONTENT,
    HTTP_200_OK
)
from rest_framework_simplejwt.tokens import RefreshToken

#Project imports
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    LoginSerializer
)
from .models import CustomUser


logger = getLogger(__name__)


class UsersViewSet(ViewSet):
    """
    Register View Set
    """
    @ratelimit(key='ip', rate='5/m', block=True)
    @action(detail=False,methods=['post'],url_path='register')
    def register(self,request)->Response:
        """
        Register a new user
        """
        email = request.data.get('request')
        serializer = RegisterSerializer(data=request.data)

        logger.info('Registering user with email: %s', email)

        if serializer.is_valid():
            user = serializer.save()
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
    

    @ratelimit(key='ip', rate='10/m', block=True)
    @action(detail=False,methods=['post'],url_path='token')
    def login(self,request)->Response:
        """
        Login a user
        """
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
                status=HTTP_201_CREATED
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


    def logout(self,request)->Response:
        """
        Logout a user
        """
        try:
            refresh_token = request.data.get['refresh']
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


    def refresh_token(self,request)->Response:
        """
        Refresh access token
        """
        try:
            refresh_token = request.data.get['refresh']
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