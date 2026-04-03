from typing import Dict, Any
import pytz
from django.utils.text import slugify
from rest_framework.serializers import (
    ModelSerializer, ValidationError,
    SerializerMethodField, PrimaryKeyRelatedField
)
from .models import Post, Comment, Tag, Category


class CategorySerializer(ModelSerializer):
    """
    Base Category Serializer
    """

    name = SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

    def get_name(self,obj):

        request = self.context.get("request")

        if request:
            lang = getattr(request, "LANGUAGE_CODE", "en")
            return obj.safe_translation_getter("name", language_code = lang, any_language = True)
        return obj.safe_translation_getter("name",any_language = True)
    

    def create(self, validated_data: Dict[str, Any]) -> Category:
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

    def create(
        self, 
        validated_data: Dict[str, Any]
    ) -> Tag:
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class PostSerializer(ModelSerializer):
    author_info = SerializerMethodField(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_published = SerializerMethodField(read_only=True)

    created_at = SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'body', 'author_info',
            'category', 'tags', 'status', 'created_at','is_published',
        ]
        read_only_fields = ['id', 'slug', 'author_info', 'created_at', 'updated_at']

    def get_author_info(self, obj: Post) -> Dict[str, Any]:
        return {
            'id': obj.author.id,
            'email': obj.author.email,
            'first_name': obj.author.first_name
        }

    def get_is_published(self, obj: Post) -> bool:
        return obj.status == Post.Status.PUBLISHED
    
    def get_created_at(self,obj):
        request = self.context.get("request")
        return self._format_date(obj.created_at, request)

    def _format_date(self, dt, request):
        if dt is None:
            return None

        if not request or not request.user.is_authenticated:
            return dt.strftime("%H:%M %d-%m-%Y UTC")
        
        user_tz_name = getattr(request.user , "timezone", "UTC")
        try:
            user_tz = pytz.timezone(user_tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            user_tz = pytz.utc

        local_dt = dt.astimezone(user_tz)

        lang = getattr(request, "LANGUAGE_CODE","en")

        if lang == "ru":
            months_ru = [
                "января", "февраля", "марта", "апреля", "мая", "июня",
                "июля", "августа", "сентября", "октября", "ноября", "декабря"
            ]
            month = months_ru[local_dt.month - 1]
            return f"{local_dt.strftime('%H:%M')} {local_dt.day} {month} {local_dt.year}"
        
        elif lang == "kk":
            months_kk = [
                "қаңтар", "ақпан", "наурыз", "сәуір", "мамыр", "маусым",
                "шілде", "тамыз", "қыркүйек", "қазан", "қараша", "желтоқсан"
            ]
            month = months_kk[local_dt.month - 1]
            return f"{local_dt.strftime('%H:%M')} {local_dt.day} {month} {local_dt.year}"
        
        return local_dt.strftime('%H:%M %d-%m-%Y')
    
        

class CreatePostSerializer(ModelSerializer):
    category = PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Post
        fields = ['title', 'body', 'category', 'tags', 'status']

    def validate_title(self, value: str) -> str:
        if len(value) < 5:
            raise ValidationError('Title must be at least 5 characters long')
        return value

    def create(
        self, 
        validated_data: Dict[str, Any]
    ) -> Post:
    
        tags_data = validated_data.pop('tags', [])
 
        title = validated_data['title']
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        validated_data['slug'] = slug
 
        post = Post.objects.create(**validated_data)
        if tags_data:
            post.tags.set(tags_data)
        return post


class EditPostSerializer(ModelSerializer):
    category = PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Post
        fields = ['title', 'body', 'category', 'tags', 'status']

    def validate_title(self, value: str) -> str:
        if len(value) < 5:
            raise ValidationError('Title must be at least 5 characters long')
        return value

    def update(
        self, 
        instance: Post, 
        validated_data: Dict[str, Any]
    ) -> Post:
        
        tags_data = validated_data.pop('tags', None)
        instance.title = validated_data.get('title', instance.title)
        instance.body = validated_data.get('body', instance.body)
        instance.category = validated_data.get('category', instance.category)
        instance.status = validated_data.get('status', instance.status)

        instance.save()
        if tags_data is not None:
            instance.tags.set(tags_data)
        return instance


class CommentSerializer(ModelSerializer):
    author_info = SerializerMethodField(read_only=True)
    post_info = SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post_info', 'author_info', 'body', 'created_at']
        read_only_fields = ['id', 'author_info', 'post_info', 'created_at']

    def get_author_info(self, obj: Comment) -> Dict[str, Any]:
        return {
            'id': obj.author.id,
            'email': obj.author.email,
            'first_name': obj.author.first_name
        }

    def get_post_info(self, obj: Comment) -> Dict[str, Any]:
        return {
            'id': obj.post.id,
            'title': obj.post.title,
            'slug': obj.post.slug
        }


class CreateCommentSerializer(ModelSerializer):

    class Meta:
        model = Comment
        fields = ['body']


    def validate_body(self, value: str) -> str:
        if len(value) < 3:
            raise ValidationError('Comment must be at least 3 characters long')
        return value


class EditCommentSerializer(ModelSerializer):
    class Meta:
        model = Comment
        fields = ['body']

    def validate_body(self, value: str) -> str:
        if len(value) < 3:
            raise ValidationError('Comment must be at least 3 characters long')
        return value

    def update(self, instance: Comment, validated_data: Dict[str, Any]) -> Comment:
        instance.body = validated_data.get('body', instance.body)
        instance.save()
        return instance