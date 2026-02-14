#Python Modules
import os 
from pathlib import Path
from datetime import timedelta

#Project Modules
from settings.conf import *



#-----------------------
#PATH
#
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_URLCONF = 'settings.urls'
WSGI_APPLICATION = 'settings.wsgi.application'
ASGI_APPLICATION = 'settings.asgi.application'
AUTH_USER_MODEL = 'users.CustomUser'


#-------------------------
#APPS
#
DJANGO_AND_THIRD_PARTY_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    #'django_ratelimit',
]
PROJECT_APPS = [
    'apps.blog',
    'apps.users'
]
INSTALLED_APPS = DJANGO_AND_THIRD_PARTY_APPS + PROJECT_APPS


#---------------------------
#MIDDLEWARE | TEMPLATES | VALIDATORS
#
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

#------------------------
#REST 
#
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}


#---------------------------------
#Simple-JWT
#
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

#---------------------------
#Logging
#
LOG_DIR = Path(BASE_DIR) / "logs"
DEBUG_LOG_PATH = LOG_DIR/"debug.log"
INFO_LOG_PATH = LOG_DIR/"info.log"
WARNING_LOG_PATH = LOG_DIR/"warning.log"
ERROR_LOG_PATH = LOG_DIR/"error.log"
CRITICAL_LOG_PATH = LOG_DIR/"critical.log"
DJANGO_REQUEST_LOG_PATH = LOG_DIR/"django_request.log"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} |{name:36s}|:{lineno:<4d} [{levelname:8s}] - {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname:8s}] - {message}",
            "style": "{",
        },
        "django_request": {
            "format": "{asctime} [{levelname:8s}] - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "simple",
        },
        "django_request_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": str(DJANGO_REQUEST_LOG_PATH),
            "formatter": "django_request",
        },
        "debug_file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(DEBUG_LOG_PATH),
            "formatter": "verbose",
            "maxBytes": 50 * 1024**2,
            "backupCount": 5,
        },
        "info_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(INFO_LOG_PATH),
            "formatter": "verbose",
            "maxBytes": 10 * 1024**2,
            "backupCount": 10,
        },
        "warning_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(WARNING_LOG_PATH),
            "formatter": "verbose",
            "maxBytes": 5 * 1024**2,
            "backupCount": 3,
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(ERROR_LOG_PATH),
            "formatter": "verbose",
            "maxBytes": 5 * 1024**2,
            "backupCount": 3,
        },
        "critical_file": {
            "level": "CRITICAL",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(CRITICAL_LOG_PATH),
            "formatter": "verbose",
            "maxBytes": 5 * 1024**2,
            "backupCount": 3,
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["django_request_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.utils.autoreload": {
            "level": "WARNING",
            "propagate": False,
        },
        "django": {
            "handlers": [
                "console",
                "debug_file",
                "info_file",
                "warning_file",
                "error_file",
                "critical_file",
            ],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": [
            "console",
            "debug_file",
            "info_file",
            "warning_file",
            "error_file",
            "critical_file",
        ],
        "level": "INFO",
    },
}

#-----------------------------
#INTERNATIONALIZATION
#
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


#-----------------------------
#STATIC
#
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR,'static')
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR,'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'