#rest_framework imports
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_204_NO_CONTENT
)
from rest_framework.permissions import IsAuthenticated, AllowAny

#Django imports
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django_ratelimit.decorators import ratelimit

#python imports
from logging import getLogger

#project imports
from .models import (
    Post,
    Comment, 
    Tag, 
    Category
)
from .serializers import (
    PostSerializer,
    EditPostSerializer,
    CreatePostSerializer,
    CommentSerializer,
    EditCommentSerializer,
    TagSerializer,
    CategorySerializer
)
from .permissions import (
    IsPublishedOrEdit,
    IsAddCommentOrReadOnly,
    IsCreatePostOrReadOnly
)

logger = getLogger(__name__)

class BlogViewSet(ViewSet):
    """
    ViewSet для управления блогом
    """
    @action(detail=False, methods=['get'], url_path='category')
    def category_list(self,request)->Response:
        """
        Получить список всех категорий
        """
        categories = Category.objects.all()
        serializer = CategorySerializer(
            categories, 
            many=True
        )
        logger.info('Retrieved %d categories', len(categories))
        return Response(
            logger.info('Categories retrieved successfully'),
            {
                'categories': serializer.data,
                'message': 'Categories retrieved successfully'
            },
            status=HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='category')
    def create_category(self,request)->Response:
        """
        Создать новую категорию
        """
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            logger.info('Category created successfully: %s', category.name)
            return Response(
                {
                    'category': CategorySerializer(category).data,
                    'message': 'Category created successfully'
                },
                status=HTTP_201_CREATED
            )
        logger.error('Failed to create category: %s', serializer.errors)
        return Response(
            {
                'errors': serializer.errors,
                'message': 'Failed to create category'
            },
            status=HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'], url_path='category/(?P<category_id>[^/.]+)')
    def category_detail(self,request,category_id)->Response:
        """
        Получить детали категории по ID
        """
        category = get_object_or_404(Category, id=category_id)
        serializer = CategorySerializer(category)
        logger.info('Retrieved category details for ID: %s', category_id)
        return Response(
            {
                'category': serializer.data,
                'message': 'Category details retrieved successfully'
            },
            status=HTTP_200_OK
        )
    

class PostViewSet(ViewSet):
    """
    ViewSet для управления постами
    """

    @action(detail=False, methods=['get'], url_path='posts')
    def posts_list(self,request)->Response:
        """
        Получить список всех постов
        """
        posts = Post.objects.all()
        serializer = PostSerializer(
            posts, 
            many=True
        )
        logger.info('Retrieved %d posts', len(posts))
        return Response(
            {
                'posts': serializer.data,
                'message': 'Posts retrieved successfully'
            },
            status=HTTP_200_OK
        )
    
     
    """Block = True - блокирует запросы, которые превышают лимит, и возвращает 429 Too Many Requests."""
    @ratelimit(key='ip', rate='10/m', block=True)
    @action(
        detail=False, 
        methods=['post'], 
        url_path='posts',
        permission_classes=[IsAuthenticated, IsCreatePostOrReadOnly]
    )
    def create_post(self,request)->Response:
        """
        Создать новый пост
        """
        serializer = CreatePostSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save(author=request.user)
            logger.info('Post created successfully: %s', post.title)
            return Response(
                {
                    'post': PostSerializer(post).data,
                    'message': 'Post created successfully'
                },
                status=HTTP_201_CREATED
            )
        logger.error('Failed to create post: %s', serializer.errors)
        return Response(
            {
                'errors': serializer.errors,
                'message': 'Failed to create post'
            },
            status=HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['get'], url_path='posts/(?P<slug>[^/.]+)')
    def post_detail(self,request,slug)->Response:
        """
        Получить детали поста по slug
        """
        post = get_object_or_404(Post, slug=slug)
        lookup_Field = 'slug'
        if post is None:
            logger.warning('Post not found for slug: %s', slug)
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        serializer = PostSerializer(post)
        logger.info('Retrieved post details for slug: %s', slug)
        return Response(
            {
                'post': serializer.data,
                'message': 'Post details retrieved successfully'
            },
            status=HTTP_200_OK
        )
    
    @action(
        detail=False, 
        methods=['put'], 
        url_path='posts/(?P<slug>[^/.]+)',
        permission_classes=[IsPublishedOrEdit]
    )
    def edit_post(self,request,slug)->Response:
        """
        Редактировать пост по slug
        """
        post = get_object_or_404(Post, slug=slug)
        if post is None:
            logger.warning('Post not found for editing with slug: %s', slug)
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        serializer = EditPostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            updated_post = serializer.save()
            logger.info('Post updated successfully: %s', updated_post.title)
            return Response(
                {
                    'post': PostSerializer(updated_post).data,
                    'message': 'Post updated successfully'
                },
                status=HTTP_200_OK
            )
        logger.error('Failed to update post: %s', serializer.errors)
        return Response(
            {
                'errors': serializer.errors,
                'message': 'Failed to update post'
            },
            status=HTTP_400_BAD_REQUEST
        )
    
    @action(
        detail=False, 
        methods=['delete'], 
        url_path='posts/(?P<slug>[^/.]+)',
        permission_classes=[IsPublishedOrEdit]
    )
    def delete_post(self,request,slug)->Response:
        """Удалить пост по slug"""
        post = get_object_or_404(Post,slug=slug)
        post.delete()
        logger.info('Post deleted successfully: %s', slug)
        return Response(
            {
                'message': 'Post deleted successfully'
            },
            status=HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'], url_path='posts/(?P<slug>[^/.]+)/comments')
    def post_comments(self,request,slug)->Response:
        """
        Получить комментарии к посту по slug
        """
        post = get_object_or_404(Post, slug=slug)
        comments = Comment.objects.filter(post=post)
        serializer = CommentSerializer(comments, many=True)
        logger.info('Retrieved %d comments for post: %s', len(comments), slug)
        return Response(
            {
                'comments': serializer.data,
                'message': 'Comments retrieved successfully'
            },
            status=HTTP_200_OK
        )
    
    @action(
        detail=False, 
        methods=['post'],
        url_path='posts/(?P<slug>[^/.]+)/comments',
        permission_classes=[IsAddCommentOrReadOnly]
    )
    def create_comment(self,request,slug)->Response:
        """
        Создать комментарий к посту по slug
        """
        post = get_object_or_404(Post, slug=slug)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(author=request.user, post=post)
            logger.info('Comment created successfully for post: %s', slug)
            return Response(
                {
                    'comment': CommentSerializer(comment).data,
                    'message': 'Comment created successfully'
                },  
                status=HTTP_201_CREATED
            )
        logger.error('Failed to create comment for post: %s, errors: %s', slug, serializer.errors)
        return Response(
            {
                'errors': serializer.errors,
                'message': 'Failed to create comment'
            },
            status=HTTP_400_BAD_REQUEST
        )