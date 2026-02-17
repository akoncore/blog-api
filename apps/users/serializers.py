from rest_framework.serializers import (
    Serializer,
    ModelSerializer,
    CharField,
    ValidationError,
    EmailField
)

from django.contrib.auth import authenticate

from .models import CustomUser


class RegisterSerializer(ModelSerializer):
    """
    User register
    """
    password = CharField(
        write_only = True,
        required = True,
    )
    password1 = CharField(
        write_only = True,
        required = True
    )

    class Meta:
        model = CustomUser
        fields = [
            'email',
            'full_name',
            'password',
            'password1'
        ]

    def validate_email(
            self,
            value:str,
    )->str:
        """Validation Email"""

        email = value.lower().strip()

        if not email:
            raise ValidationError(
                {
                    'error':'There is not email'
                }
            )
        return email
    
    def validate_full_name(
            self,
            value:str,
    )->str:
        """Validtion full_name"""

        full_name = value.strip()

        if not full_name and len(full_name<2):
            raise ValidationError(
                {
                    'error':'Error full_name'
                }
            )
        return full_name.title()
    
    def validate(
            self, 
            attrs:str
        )->str:
        password = attrs.get('password')
        password1 = attrs.get('password1')

        if password != password1:
            raise ValidationError(
                {
                    'error':'Password is non correct'
                }
            )
        return attrs

    def create(
            self,
            validated_data
        ):
        ""
        validated_data.pop('password1')

        user = CustomUser.objects.create_user(**validated_data)
        return user


class LoginSerializer(Serializer):
    """
    Serializer Login
    """
    email = EmailField()
    password = CharField(
        write_only = True,
        required = True
    )

    class Meta:
        model = CustomUser
        fields = [
            'email',
            'password'
        ]

    def valdate_email(
            self,
            value:str
    )->str:
        """Normalize email"""
        email = value.lower().strip()
        return email
    
    def validate(self, attrs):
        """Validate email and password"""
        email = attrs.get('email')
        password = attrs.get('password')

        if not email and password:
            raise ValidationError(
                {
                    'error':"There is not email or password"
                }
            )
        
        user = authenticate(
            request=self.context.get('request'),
            email = email,
            password = password
        )

        if not user.is_active:
            raise ValidationError(
                {
                    'error':'User is deactivate'
                }
            )
        
        if not user:
            raise ValidationError(
                {
                    'error':"User is not"
                }
            )
        attrs['user'] = user
        attrs['email'] = user.email
        return attrs
    

class UserProfileSerializer(ModelSerializer):
    """
    User profile
    """
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'full_name',
            'is_active'
        ]


class UpdateUserProfileSerializer(ModelSerializer):
    """
    Update user profile
    """
    class Meta:
        model = CustomUser
        fields = [
            'full_name'
        ]


class ChangePasswordSerializer(ModelSerializer):
    """
    Change password 
    """
    old_password = CharField(
        write_only = True,
        required = True
    )
    new_password = CharField(
        write_only = True,
        required = True
    )
    new_password_confirm = CharField(
        write_only = True,
        required = True
    )

    def validate_old_password(
            self,
            value:str
    )->str:
        """Serializer old password"""
        user = self.context['request'].user

        if not user.check_password(value):
            raise ValidationError(
                {
                    'error':"Old password is not correct"
                }
            )
        
    def validate(self, attrs):
        """Validate all serializer data"""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')

        if new_password != new_password_confirm:
            raise ValidationError(
                {
                    'error':"Non correct"
                }
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
   



    


