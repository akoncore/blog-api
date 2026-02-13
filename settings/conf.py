from decouple import config
from datetime import timedelta


#-----------------------------
#ENV_ID
#
ENV_POSSIBLE_OPTIONS = (
    "local",
    "prod"
)
ENV_ID = config("BLOG_ENV_ID",cast=str)
SECRET_KEY = 'django-insecure-+ada5^xvx&doe5tpzsdnlu6qb%llv6*^#4l@rh@tz((5*!u!vw'


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