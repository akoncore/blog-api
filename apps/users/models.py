
#python modules
from typing import Any

from django.db.models import (
    CharField,
    EmailField,
    BooleanField,
    DateTimeField,
    ImageField
    
)
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin
)
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    """
    User Manager - handles user creation
    """
    def __obtain_user_instance(
            self,
            email:str,
            full_name:str,
            password:str,
            **kwargs:dict[str,Any],
    )-> 'CustomUser':
        """
        Get user instance,
        """
        if not email:
            raise ValidationError(
                message="Email field is required",
                code="email_empty"
            )
        if not full_name:
            raise ValidationError(
                message="Full name is required",
                code="full_name_empty"
            )
        
        new_user:'CustomUser' = self.model(
            email = self.normalize_email(email),
            full_name = full_name,
            password = password,
            **kwargs,
        )
        return new_user
    
    def create_user(
        self,
        email:str,
        full_name:str,
        password:str,
        **kwargs:dict[str,Any],
    )->'CustomUser':
        """
        Create Cutom User. TODO where is this used?
        """
        new_user: 'CustomUser' = self.__obtain_user_instance(
            email=email,
            full_name=full_name,
            password=password,
            **kwargs,
        )
        new_user.set_password(password)
        new_user.save(using=self.db)
        return new_user
    
    def create_superuser(
            self,
            email:str,
            full_name:str,
            password:str,
            **kwargs:dict[str,Any],
    )-> 'CustomUser':
        """
        Create Superuser
        """
        new_user: 'CustomUser' = self.__obtain_user_instance(
            email=email,
            full_name=full_name,
            password=password,
            is_active=True,
            is_staff=True,
            is_superuser=True,
            **kwargs,
        )
        new_user.set_password(password)
        new_user.save(using=self.db)
        return new_user


class CustomUser(AbstractBaseUser,PermissionsMixin):
    """
    Model CustomUser
    """
    email = EmailField(
        unique=True,
        max_length=100,
        db_index=True,
        help_text="User email address",
        verbose_name="Email address"
    )
    full_name = CharField(
        max_length=100,
        verbose_name="User full name"
    )
    password = CharField(
        max_length=200,
        verbose_name="Password"
    )
    is_active = BooleanField(
        default=True,
        verbose_name="Statuc activate"
    )
    is_staff = BooleanField(
        default=False,
        verbose_name="Staff status"
    )
    data_joined = DateTimeField(
        auto_now_add=True
    )
    avatar = ImageField(
        blank=True,
        null=True,
    )

    REQUIRED_FIELDS = ["full_name"]
    USERNAME_FIELD = "email"
    objects = CustomUserManager()

    class Meta:
        """
        Meta options for CustomUser model
        """
        verbose_name = "Custom User"
        ordering = ["full_name"]
