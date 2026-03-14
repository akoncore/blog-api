from rest_framework.serializers import (
    Serializer, ModelSerializer, CharField, ValidationError, EmailField,ChoiceField
)
from django.contrib.auth import authenticate
from .models import CustomUser , PREFERRED_LANGUAGES

import pytz

SUPPORTED_LANGUAGE_CODES = [code for code, _ in PREFERRED_LANGUAGES]

class RegisterSerializer(ModelSerializer):
    password = CharField(write_only=True, required=True)
    password1 = CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'full_name', 'password', 'password1']

    def validate_email(self, value: str) -> str:
        email = value.lower().strip()
        if not email:
            raise ValidationError({'error': 'There is not email'})
        return email

    def validate_full_name(self, value: str) -> str:
        
        full_name = value.strip()
        if not full_name or len(full_name) < 2:
            raise ValidationError({'error': 'Full name must be at least 2 characters'})
        return full_name.title()

    def validate(self, attrs: dict) -> dict:
        if attrs.get('password') != attrs.get('password1'):
            raise ValidationError({'error': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password1')
        return CustomUser.objects.create_user(**validated_data)


class LoginSerializer(Serializer):
    email = EmailField()
    password = CharField(write_only=True, required=True)

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate(self, attrs: dict) -> dict:
        email = attrs.get('email')
        password = attrs.get('password')
        if not email or not password:
            raise ValidationError({'error': 'Email and password are required'})
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password
        )
        if not user:
            raise ValidationError({'error': 'Invalid credentials'})
        if not user.is_active:
            raise ValidationError({'error': 'User account is deactivated'})
        attrs['user'] = user
        attrs['email'] = user.email
        return attrs


class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'full_name', 'is_active']


class UpdateUserProfileSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['full_name']


class ChangePasswordSerializer(Serializer):

    old_password = CharField(write_only=True, required=True)
    new_password = CharField(write_only=True, required=True)
    new_password_confirm = CharField(write_only=True, required=True)


    def validate_old_password(self, value: str) -> str:

        if not user.check_password(value):
            raise ValidationError(
                {
                    'error':"Old password is not correct"
                }
            )

        
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError({'error': 'Old password is incorrect'})
        return value  

    def validate(self, attrs: dict) -> dict:
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise ValidationError({'error': 'New passwords do not match'})
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
    
class LanguagesSerializer(Serializer):
    preferred_language = ChoiceField(
        choices=SUPPORTED_LANGUAGE_CODES
    )

class TimezoneSerializer(Serializer):
    timezone = CharField(
        max_length = 100
    )

    def validate_timezone(self,value):
        if value not in pytz.all_timezones:
            raise ValidationError(
                f"'{value}' is not a valid IANA timezone. "
                f"Examples: UTC, Asia/Almaty, Europe/Moscow, America/New_York"
            )
        return value