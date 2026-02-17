from django.contrib.admin import (
    ModelAdmin,
    register
)

from .models import (
    Post,
    Tag,
    Category,
    Comment
)

@register(Post)
class PostAdmin(ModelAdmin):
    list_display = (
        'author',
        'title',
        'body',
        'category',
        'status'
    )
    list_editable = ('category',)
    ordering = ('category',)
    list_filter = ('category',)


@register(Tag)
class TagAdmin(ModelAdmin):
    list_display = (
        'name',
    )
    search_fields = ('name',)


@register(Category)
class CatgoryAdmin(ModelAdmin):
    list_display = (
        'name',
    )
    search_fields = (
        'name',
    )


@register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = (
        'post',
        'author',
        'created_at',
    )
    list_display_links = ('post',)
    

