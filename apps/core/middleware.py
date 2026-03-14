import pytz

from django.conf import settings
from django.utils import translation,timezone

from rest_framework_simplejwt.authentication import JWTAuthentication


class LanguageAndTimezoneMiddleware:
    """
    The language the authenticated user has saved in their profile
    A ?lang= query parameter in the URL
    The Accept-Language HTTP header sent by the client
    The default language configured in settings (en)

    TIMEZONE:
        -Authenticated user 'timezone' field 

    """

    def __init__(self,get_response):
        self.get_response = get_response
        self._jwt_auth = JWTAuthentication()


    #Entry pointpass
    def __call__(self, request,*args, **kwds):
        self._try_authenticate_jwt(request)

        lang = self._resolve_language(request)
        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        self._activate_timezone(request)

        try:
            return self.get_response(request)
        finally:
            translation.deactivate()
            timezone.deactivate()


    #JWT Authentication
    def _try_authenticate_jwt(self,request) ->None:
        if request.user.is_authenticated:
            return

        try:
            result = self._jwt_auth.authenticate(request)
            if result is not None:
                request.user, _ = result
        except Exception:
            pass

    
    #Language
    def _resolve_language(self,request)->str:
        supported: set = set(settings.SUPPORTED_LANGUAGES)

        return(
            self._lang_form_user(request,supported)
            or self._lang_from_query(request,supported)
            or self._lang_from_accept_header(request,supported)
            or settings.LANGUAGE_CODE
        )
    
    @staticmethod
    def _lang_form_user(request,supported:set)->str | None:
        if request.user.is_authenticated:
            lang = getattr(request.user, "preferred_language", None)
            if lang in supported:
                return lang
        return None
    
    @staticmethod
    def _lang_from_query(request,supported:set)->str | None:
        lang = request.GET.get("lang")
        return lang if lang in supported else None
    
    @staticmethod
    def _lang_from_accept_header(request,supported:set)-> str | None:
        accept_header = request.META.get('HTTP_ACCEPT_LANGUAGE',"")
        for segment in accept_header.split(","):
            code = segment.strip().split(",")[0].strip()[:2].lower()
            if code in supported:
                return code
        return None
    

    #timezone
    def _activate_timezone(self,request)-> None:
        tz = self._resolve_timezone(request)
        timezone.activate(tz)

    @staticmethod
    def _resolve_timezone(request)->pytz.BaseTzInfo:
        if request.user.is_authenticated:
            tz_name = getattr(request.user, "timezone", None)
            if tz_name:
                try:
                    return pytz.timezone(tz_name)
                except pytz.exceptions.UnknownTimeZoneError:
                    pass
        return pytz.utc
    

