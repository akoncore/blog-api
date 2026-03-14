from django.contrib.admin import (
    ModelAdmin,
    register,

)
from .models import (
    CustomUser
)


@register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = (
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'is_active',
    )
    list_display_links = ('email',)
    search_fields = ('email','first_name',)
    ordering = ('email',)
    
