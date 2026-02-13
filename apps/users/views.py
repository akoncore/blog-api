from logging import getLogger

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action

from .serializers import (
    RegisterSerializer,
)
from .models import CustomUser


logger = getLogger(__name__)

class UsersViewSet(ViewSet):
    """
    Register View Set
    """
    @action(detail=False,methods=['post'],url_path='register')
    def register(self,request):
        email = request.data.get('request')
        seriali
