# Standard library
from typing import Dict, Any

# Django imports
from django.utils.text import slugify

# REST Framework imports
from rest_framework.serializers import (
    ModelSerializer,
    CharField,
    ValidationError,
    SerializerMethodField,
    BooleanField,
    PrimaryKeyRelatedField
)

# Project imports
from .models import (
    Post,
    Comment,
    Tag,
    Category
)


class CategorySerializer(ModelSerializer):
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

    def create(self, validated_data: Dict[str, Any]) -> Category:
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class TagSerializer(ModelSerializer):
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

    def create(self, validated_data: Dict[str, Any]) -> Tag:
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)


class PostSerializer(ModelSerializer):
    
    author_info = SerializerMethodField(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_published = SerializerMethodField(read_only=True)

    class Meta:
        
        model = Post
        fields = [
            'id',
            'title',
            'slug',
            'body',
            'author_info',
            'category',
            'tags',
            'status',
            'created_at',
            'updated_at',
            'is_published',
        ]
        read_only_fields = ['id', 'slug', 'author_info', 'created_at', 'updated_at']

    def get_author_info(self, obj: Post) -> Dict[str, Any]:
        author = obj.author
        return {
            'id': author.id,
            'email': author.email,
            'full_name': author.full_name
        }
    
    def get_is_published(self, obj: Post) -> bool:
        return obj.status == Post.Status.PUBLISHED


class CreatePostSerializer(ModelSerializer):
    
    category = PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )
    
    class Meta:

        model = Post
        fields = [
            'title',
            'body',
            'category',
            'tags',
            'status',
        ]

    def validate_title(self, value: str) -> str:
        if len(value) < 5:
            raise ValidationError('Title must be at least 5 characters long')
        return value

    def create(self, validated_data: Dict[str, Any]) -> Post:

        tags_data = validated_data.pop('tags', [])

        post = Post.objects.create(**validated_data)
        
        if tags_data:
            post.tags.set(tags_data)
        
        return post


class EditPostSerializer(ModelSerializer):
    
    category = PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )

    class Meta:

        model = Post
        fields = [
            'title',
            'body',
            'category',
            'tags',
            'status',
        ]

    def validate_title(self, value: str) -> str:
        if len(value) < 5:
            raise ValidationError('Title must be at least 5 characters long')
        return value

    def update(self, instance: Post, validated_data: Dict[str, Any]) -> Post:
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
        fields = [
            'id',
            'post_info',
            'author_info',
            'body',
            'created_at',

        ]
        read_only_fields = ['id', 'author_info', 'post_info', 'created_at']

    def get_author_info(self, obj: Comment) -> Dict[str, Any]:
        author = obj.author
        return {
            'id': author.id,
            'email': author.email,
            'full_name': author.full_name
        }
    
    def get_post_info(self, obj: Comment) -> Dict[str, Any]:
        post = obj.post
        return {
            'id': post.id,
            'title': post.title,
            'slug': post.slug
        }


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