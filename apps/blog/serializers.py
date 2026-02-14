#Django imports
from django.utils.text import slugify

#REST Framework imports
from rest_framework.serializers import (
    ModelSerializer,
    CharField,
    ValidationError,
    SerializerMethodField,
    BooleanField
)

#Project imports
from .models import (
    Post,
    Comment,
    Tag,
    Category
)


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug'
        ]

    def create(self, validated_data):
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    

class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            'id',
            'name',
            'slug'
        ]

    def create(self, validated_data):
        validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)
    

class PostSerializer(ModelSerializer):
    author_info = SerializerMethodField(read_only=True)
    category = CategorySerializer()
    tags = TagSerializer(many=True)
    is_published = SerializerMethodField(read_only=True)

    class Meta:
        """Serializer for Post model"""
        model = Post
        fields = [
            'id',
            'title',
            'content',
            'author_info',
            'category',
            'tags',
            'created_at',
            'updated_at',
            'is_published',
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_info(self, obj):
        author = obj.author
        return {
            'id': author.id,
            'email': author.email,
            'full_name': author.full_name
        }
    
    def get_is_published(self, obj):
        return obj.status == Post.Status.PUBLISHED


class CreatePostSerializer(ModelSerializer):
    is_published = BooleanField(read_only=True, default=False)
    class Meta:
        """Serializer for creating Post model"""
        model = Post
        fields = [
            'title',
            'content',
            'category',
            'tags',
            'is_published'
        ]

    def create(self, validated_data):
        category_data = validated_data.pop('category', None)
        tags_data = validated_data.pop('tags', [])

        post = Post.objects.create(**validated_data)

        if category_data:
            category, _ = Category.objects.get_or_create(**category_data)
            post.category = category

        for tag_data in tags_data:
            tag, _ = Tag.objects.get_or_create(**tag_data)
            post.tags.add(tag)

        if validated_data.get('is_published'):
            post.status = Post.Status.PUBLISHED
            
        post.save()
        return post
    

class EditPostSerializer(ModelSerializer):

    class Meta:
        """Serializer for editing Post model"""
        model = Post
        fields = [
            'title',
            'content',
            'category',
            'tags',
            'status'
        ]

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)

        category_data = validated_data.get('category')
        if category_data:
            category, _ = Category.objects.get_or_create(**category_data)
            instance.category = category

        tags_data = validated_data.get('tags')
        if tags_data is not None:
            instance.tags.clear()
            for tag_data in tags_data:
                tag, _ = Tag.objects.get_or_create(**tag_data)
                instance.tags.add(tag)

        instance.status = validated_data.get('status', instance.status)
        instance.save()
        return instance


class CommentSerializer(ModelSerializer):
    author_info = SerializerMethodField(read_only=True)
    post = SerializerMethodField(read_only=True)
    class Meta:
        """Serializer for Comment model"""
        model = Comment
        fields = [
            'id',
            'post',
            'author',
            'content',
            'created_at',
            'updated_at',
            'author_info'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_info(self, obj):
        author = obj.author
        return {
            'id': author.id,
            'email': author.email,
            'full_name': author.full_name
        }
    
    def get_post(self, obj):
        post = obj.post
        return {
            'id': post.id,
            'title': post.title,
            'slug': post.slug
        }
    

class EditCommentSerializer(ModelSerializer):
    class Meta:
        """Serializer for editing Comment model"""
        model = Comment
        fields = [
            'content'
        ]

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance