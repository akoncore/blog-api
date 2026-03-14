#Python modules
from typing import Any
import json
from logging import getLogger

#Django modules
from django.core.cache import cache
from django.db.models import Q


#REST Framework
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK, 
    HTTP_201_CREATED, 
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND, 
    HTTP_204_NO_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS, 
    HTTP_401_UNAUTHORIZED, 
    HTTP_403_FORBIDDEN
)
from rest_framework.permissions import AllowAny

#drf-spectular
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)

#Project modules
from .models import Post, Comment
from .serializers import (
    PostSerializer, EditPostSerializer, CreatePostSerializer,
    CommentSerializer, EditCommentSerializer, CreateCommentSerializer

)
from .permissions import (
    IsPublishedOrEdit, IsAddCommentOrReadOnly, IsCreatePostOrReadOnly
)


logger = getLogger(__name__)


def is_rate_limited(
    request, 
    action_name, 
    limit
) -> bool:
    ip = request.META.get('REMOTE_ADDR')
    cache_key = 'rate_limit_%s_%s' % (action_name, ip)
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    cache.set(cache_key, count + 1, timeout=60)
    return False


def rate_limit_response(
    request, 
    exception
) -> Response:
    logger.warning(
        f"Rate limit exceeded for user: "
        f"{request.user.id if request.user.is_authenticated else 'Anonymous'} "
        f"from IP: {request.META.get('REMOTE_ADDR')}"
    )
    return Response(
        {'detail': 'Rate limit exceeded. Please try again later.'},
        status=HTTP_429_TOO_MANY_REQUESTS
    )


def publish_comment_event(
    comment: Comment
) -> None:
    try:
        redis_client = cache.client.get_client()

        event_data = {
            'event': 'comment_published',
            'data': {
                'comment_id': comment.id,
                'post_id': comment.post.id,
                'post_title': comment.post.title,
                'author_id': comment.author.id,
                'author_name': comment.author.full_name,
                'content': comment.body,
                'created_at': comment.created_at.isoformat()
            }
        }

        message = json.dumps(event_data, default=str)
        redis_client.publish('comments', message)
        logger.info(f"Published comment event for comment id: {comment.id}")

    except Exception as e:
        logger.error(f"Failed to publish comment event: {str(e)}")


@extend_schema_view(
    list=extend_schema(
        summary='List all posts',
        description='Returns a list of all published posts or user-authored posts',
        tags=['Posts'],
        responses={
            200: OpenApiResponse(
                response=PostSerializer(many=True),
                description="List of posts"
            ),
            204: OpenApiResponse(
                description="No posts available"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            403: OpenApiResponse(
                description="Access denied"
            ),
        },
    ),
    retrieve=extend_schema(
        summary='Retrieve a post by slug',
        description='Returns post detail by slug',
        tags=['Posts'],
        responses={
            200: OpenApiResponse(
                response=PostSerializer,
                description="Post details"
            ),
            404: OpenApiResponse(
                description="Post not found"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            403: OpenApiResponse(
                description="Access denied"
            ),
        },
    ),
    create=extend_schema(
        summary='Create a new post',
        description='Authenticated users can create a new post',
        tags=['Posts'],
        request=CreatePostSerializer,
        responses={
            201: OpenApiResponse(
                response=PostSerializer,
                description="Post created successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            429: OpenApiResponse(
                description="Rate limit exceeded"
            ),
        },
    ),
    update=extend_schema(
        summary='Update a post',
        description='Author can update their own post',
        tags=['Posts'],
        request=EditPostSerializer,
        responses={
            200: OpenApiResponse(
                response=PostSerializer,
                description="Post updated successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            403: OpenApiResponse(
                description="Permission denied"
            ),
            404: OpenApiResponse(
                description="Post not found"
            ),
        },
    ),
    destroy=extend_schema(
        summary='Delete a post',
        description='Author can delete their own post',
        tags=['Posts'],
        responses={
            204: OpenApiResponse(
                description="Post deleted successfully"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            403: OpenApiResponse(
                description="Permission denied"
            ),
            404: OpenApiResponse(
                description="Post not found"
            ),
        },
    ),
    comments=extend_schema(
        summary='Comments for a post',
        description='List or create comments for a specific post',
        tags=['Posts'],
        request=CreateCommentSerializer,
        responses={
            200: OpenApiResponse(
                response=CommentSerializer(many=True),
                description="List of comments"
            ),
            201: OpenApiResponse(
                response=CommentSerializer,
                description="Comment created successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
            404: OpenApiResponse(
                description="Post not found"
            ),
        },
    ),
)


class PostViewSet(ViewSet):
    """
    GET    /api/posts/              — published постарды тізімдейді
    POST   /api/posts/              — жаңа пост жасайды (auth)
    GET    /api/posts/{slug}/       — бір постты қайтарады
    PATCH  /api/posts/{slug}/       — постты жаңартады (тек автор)
    DELETE /api/posts/{slug}/       — постты өшіреді (тек автор)
    GET    /api/posts/{slug}/comments/ — комменттерді тізімдейді
    POST   /api/posts/{slug}/comments/ — коммент қосады (auth)
    """
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsPublishedOrEdit]
        elif self.action == 'create':
            permission_classes = [IsCreatePostOrReadOnly]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsPublishedOrEdit]
        elif self.action == 'comments':
            permission_classes = [IsAddCommentOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def list(
        self, 
        request
) -> Response:
        
        user_info = (
            f"{request.user.id} - {request.user.email}"
            if request.user.is_authenticated else "Anonymous"
        )
        logger.info(f"Post list requested by {user_info}")

        if request.user.is_authenticated:

            queryset = Post.objects.filter(
                Q(status=Post.Status.PUBLISHED) | Q(author=request.user)
            ).select_related('author', 'category').prefetch_related('tags')

            serializer = PostSerializer(queryset, many=True)
            return Response(
                {
                    'posts': serializer.data, 
                    'total_posts': queryset.count()
                },
                status=HTTP_200_OK
            )

        cache_key = 'published_posts'
        lang = getattr(request, "LANGUAGE_CODE","en")
        cache_key = f"Published_posts_{lang}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Cache hit for published posts")
            return Response(
                {'posts': cached_data, 'total_posts': len(cached_data)},
                status=HTTP_200_OK
            )

        queryset = Post.objects.filter(
            status=Post.Status.PUBLISHED
        ).select_related('author', 'category').prefetch_related('tags')
        serializer = PostSerializer(queryset, many=True)
        response_data = serializer.data
        cache.set(cache_key, response_data, timeout=60)
        logger.info("Published posts cached for 60 seconds")

        return Response(
            {'posts': response_data, 'total_posts': queryset.count()},
            status=HTTP_200_OK
        )

    def create(
        self, 
        request, 
        *args, 
        **kwargs
    ) -> Response:
        
        if is_rate_limited(request, 'create', 20):
            return rate_limit_response(request, None)

        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to create a post'},
                status=HTTP_401_UNAUTHORIZED
            )

        serializer = CreatePostSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            post = serializer.save(author=request.user)
            cache.delete('published_posts')
            from django.conf import settings as django_settings
            for lang_code in django_settings.SUPPORTED_LANGUAGES:
                cache.delete(f"published_posts{lang_code}")
            logger.info(f"Post created by {request.user.email}: {post.title}")
            return Response(
                {
                    'message': 'Post created successfully', 
                    'post': PostSerializer(post).data
                },
                status=HTTP_201_CREATED
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def retrieve(
        self, 
        request, 
        slug=None
    ) -> Response:
       
        try:
            post = Post.objects.select_related(
                'author', 'category'
            ).prefetch_related('tags').get(slug=slug)

        except Post.DoesNotExist:
            return Response(
                {'error': 'Post not found'}, 
                status=HTTP_404_NOT_FOUND
            )

        
        if post.status == Post.Status.DRAFT:
            if not request.user.is_authenticated or post.author != request.user:
                return Response(
                    {'error': 'Post not found'},
                    status=HTTP_404_NOT_FOUND
                )

        serializer = PostSerializer(post)
        return Response(
            serializer.data, 
            status=HTTP_200_OK
        )

    def update(
        self,
        request, 
        slug=None
    ) -> Response:
        
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to update a post'},
                status=HTTP_401_UNAUTHORIZED
            )
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return Response(
                {'error': 'Post not found'}, 
                status=HTTP_404_NOT_FOUND
            )

        if post.author != request.user:
            return Response(
                {'error': 'You do not have permission to edit this post'},
                status=HTTP_403_FORBIDDEN
            )

        serializer = EditPostSerializer(
            post, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():

            updated_post = serializer.save()
            cache.delete('published_posts')
            from django.conf import settings as django_settings
            for lang_code in django_settings.SUPPORTED_LANGUAGES:
                cache.delete(f"published_posts{lang_code}")
            logger.info(f"Post updated by {request.user.email}: {updated_post.title}")

            return Response(
                {'message': 'Post updated successfully', 'post': PostSerializer(updated_post).data},
                status=HTTP_200_OK
            )
        
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def destroy(
        self, 
        request, 
        slug=None
    ) -> Response:
        
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to delete a post'},
                status=HTTP_401_UNAUTHORIZED
            )
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=HTTP_404_NOT_FOUND)

        if post.author != request.user:
            return Response(
                {'error': 'You do not have permission to delete this post'},
                status=HTTP_403_FORBIDDEN
            )

        title = post.title
        post.delete()
        cache.delete('published_posts')
        from django.conf import settings as django_settings
        for lang_code in django_settings.SUPPORTED_LANGUAGES:
            cache.delete(f"published_posts{lang_code}")
        logger.info(f"Post deleted by {request.user.email}: {title}")

        return Response(
            {'message': 'Post deleted successfully'}, 
            status=HTTP_204_NO_CONTENT
        )

    @action(
        detail=True, 
        methods=['get', 'post'], 
        url_path='comments'
    )
    def comments(
        self, 
        request, 
        slug=None
    ) -> Response:
        try:
            post = Post.objects.get(slug=slug)
        except Post.DoesNotExist:
            return Response(
                {'error': 'Post not found'}, 
                status=HTTP_404_NOT_FOUND
            )

        if post.status == Post.Status.DRAFT:
            if not request.user.is_authenticated or post.author != request.user:
                return Response(
                    {'error': 'Post not found'},
                    status=HTTP_404_NOT_FOUND
                )

        if request.method == 'GET':
            comments = post.comments.all().select_related('author').order_by('-created_at')
            serializer = CommentSerializer(comments, many=True)
            return Response(
                serializer.data, 
                status=HTTP_200_OK
            )

        elif request.method == 'POST':
            if not request.user.is_authenticated:
                logger.warning("Unauthorized comment creation attempt by anonymous user")
                return Response(
                    {
                        'error': 'Authentication required to add a comment'
                    },
                    status=HTTP_401_UNAUTHORIZED
                )
            serializer = CreateCommentSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                comment = serializer.save(author=request.user, post=post)


        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to add a comment'},
                status=HTTP_401_UNAUTHORIZED
            )

        serializer = CreateCommentSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            comment = serializer.save(author=request.user, post=post)
            publish_comment_event(comment)
            logger.info(f"Comment added by {request.user.email} to post: {post.title}")
            return Response(
                {'message': 'Comment added successfully', 'comment': CommentSerializer(comment).data},
                status=HTTP_201_CREATED
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary='List all comments',
        description='Returns a list of all comments for published posts',
        tags=['Comments'],
        responses={
            200: OpenApiResponse(
                response=CommentSerializer(many=True),
                description='List of comments'
            ),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Access denied'),
        }
    ),
    retrieve=extend_schema(
        summary='Retrieve a comment by ID',
        description='Returns a comment by its ID',
        tags=['Comments'],
        responses={
            200: OpenApiResponse(
                response=CommentSerializer,
                description='Comment details'
            ),
            404: OpenApiResponse(description='Comment not found'),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Access denied'),
        }
    ),
    partial_update=extend_schema(
        summary='Update a comment',
        description='Authenticated users can update their own comments',
        tags=['Comments'],
        request=EditCommentSerializer,
        responses={
            200: OpenApiResponse(
                response=CommentSerializer,
                description='Comment updated successfully'
            ),
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Comment not found'),
        }
    ),
    destroy=extend_schema(
        summary='Delete a comment',
        description='Authenticated users can delete their own comments',
        tags=['Comments'],
        responses={
            204: OpenApiResponse(description='Comment deleted successfully'),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='Comment not found'),
        }
    ),
)


class CommentViewSet(ViewSet):
    """
    GET    /api/comments/       — барлық комменттер (тек published посттікі)
    GET    /api/comments/{id}/  — бір коммент
    PATCH  /api/comments/{id}/  — өз коммент жаңарту (auth)
    DELETE /api/comments/{id}/  — өз комментті өшіру (auth)
    """

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            permission_classes = [IsAddCommentOrReadOnly]
        elif self.action in ['partial_update', 'destroy']:
            permission_classes = [IsAddCommentOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def list(self, request) -> Response:

        queryset = Comment.objects.filter(
            post__status=Post.Status.PUBLISHED
        ).select_related('author', 'post').order_by('-created_at')

        serializer = CommentSerializer(queryset, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def retrieve(self, request, pk=None) -> Response:
        try:
            comment = Comment.objects.select_related('author', 'post').get(pk=pk)
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        
        if comment.post.status == Post.Status.DRAFT:
            if not request.user.is_authenticated or comment.post.author != request.user:
                return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        serializer = CommentSerializer(comment)
        return Response(serializer.data, status=HTTP_200_OK)

    def destroy(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to delete a comment'},
                status=HTTP_401_UNAUTHORIZED
            )
        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        if comment.author != request.user:
            return Response(
                {'error': 'You do not have permission to delete this comment'},
                status=HTTP_403_FORBIDDEN
            )

        comment.delete()
        logger.info(f"Comment {pk} deleted by {request.user.email}")
        return Response({'message': 'Comment deleted successfully'}, status=HTTP_204_NO_CONTENT)

    def partial_update(self, request, pk=None) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required to update a comment'},
                status=HTTP_401_UNAUTHORIZED
            )
        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=HTTP_404_NOT_FOUND)

        if comment.author != request.user:
            return Response(
                {'error': 'You do not have permission to edit this comment'},
                status=HTTP_403_FORBIDDEN
            )

        serializer = EditCommentSerializer(
            comment, data=request.data, partial=True, context={'request': request}
        )
        if serializer.is_valid():
            updated_comment = serializer.save()
            logger.info(f"Comment {pk} updated by {request.user.email}")
            return Response(
                {'message': 'Comment updated successfully', 'comment': CommentSerializer(updated_comment).data},
                status=HTTP_200_OK
            )
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)