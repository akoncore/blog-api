#rest_framework imports
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_204_NO_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS
)
from rest_framework.permissions import IsAuthenticated, AllowAny

#Django imports
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit

#python imports
from logging import getLogger
import hashlib
import json
import time

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


 #------------------
 #Helper functions
#------------------
def rate_limit_handler(request, exception):
    """
    Обработчик для превышения rate limit.
    Возвращает стандартный JSON ответ с 429 статусом.
    """
    logger.warning(f'Rate limit exceeded for {request.path} by {request.META.get("REMOTE_ADDR")}')
    return Response(
        {'detail': 'Too many requests. Try again later.'},
        status=HTTP_429_TOO_MANY_REQUESTS
    )


def invalidate_posts_cache():
    """
    Инвалидирует кеш списка постов.
    
    Удаляет все ключи с префиксом 'posts_list_' из Redis.
    Вызывается при создании, обновлении или удалении постов.
    """
    try:
        redis_client = cache.client.get_client()
        pattern = 'myapp:1:posts_list_*'
        
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f'Cache invalidated: {len(keys)} keys deleted')
    except Exception as e:
        logger.error(f'Failed to invalidate cache: {e}')


def publish_comment_event(comment: Comment):
    """
    Публикует событие о создании комментария в Redis Pub/Sub канал 'comments'.
    
    Args:
        comment: Instance созданного комментария
    """
    try:
        redis_client = cache.client.get_client()
        
        # Формируем событие
        event = {
            'event': 'comment_created',
            'timestamp': time.time(),
            'data': {
                'id': comment.id,
                'post_id': comment.post.id,
                'post_title': comment.post.title,
                'post_slug': comment.post.slug,
                'author_id': comment.author.id,
                'author_email': comment.author.email,
                'author_name': comment.author.full_name,
                'body': comment.body,
                'created_at': comment.created_at.isoformat(),
            }
        }
        
        # Публикуем в канал
        message = json.dumps(event, ensure_ascii=False)
        num_subscribers = redis_client.publish('comments', message)
        
        logger.info(
            f'Published comment_created event for comment {comment.id} '
            f'to {num_subscribers} subscriber(s)'
        )
        
    except Exception as e:
        logger.error(f'Failed to publish comment event: {e}')


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

    def generate_cache_key(self, request):
        """
        Генерирует уникальный ключ для кэширования на основе IP-адреса и URL запроса.
        """
        params = {
            'page': request.query_params.get('page', ''),
            'ordering': request.query_params.get('ordering', '-created_at'),
            'search': request.query_params.get('search', ''),
            'category': request.query_params.get('category', ''),
            'status': request.query_params.get('status', 'published'),
        }

        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        return f"posts_list_{params_hash}"

    @action(detail=False, methods=['get'], url_path='posts')
    def posts_list(self,request)->Response:
        """
        Получить список всех постов
        """
        cache_key = self._generate_cache_key(request)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            # Cache HIT - данные найдены в Redis
            logger.info(f'[CACHE HIT] {cache_key}')
            return Response(cached_data, status=HTTP_200_OK)

        posts = Post.objects.filter(status='published').select_related(
            'author', 'category'
        ).prefetch_related(
            'tags'
        )
        serializer = PostSerializer(
            posts, 
            many=True
        )

        response_data = {
            'posts': serializer.data,
            'message': 'Posts retrieved successfully'
        }
        cache.set(cache_key, response_data, timeout=60)
        logger.info(f'[CACHED] {cache_key} for 60 seconds')

        logger.info('Retrieved %d posts', len(posts))
        return Response(
            response_data,
            status=HTTP_200_OK
        )
    
     
    """Block = True - блокирует запросы, которые превышают лимит, и возвращает 429 Too Many Requests."""
    @ratelimit(key='user_or_ip', rate='20/m',method='POST', block=True)
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

        if getattr(request, 'limited', False):
            return rate_limit_handler(request, None)

        serializer = CreatePostSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save(author=request.user)

            invalidate_posts_cache()

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