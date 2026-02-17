
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
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_401_UNAUTHORIZED
)
from rest_framework.permissions import  AllowAny

#Django imports
from django.core.cache import cache
from django.db.models import Q


#python imports
from logging import getLogger
from typing import Any
import json


#project imports
from .models import (
    Post,
    Comment, 
    
)

from .serializers import (
    PostSerializer,
    EditPostSerializer,
    CreatePostSerializer,
    CommentSerializer,
    EditCommentSerializer,

)
from .permissions import (
    IsPublishedOrEdit,
    IsAddCommentOrReadOnly,
    IsCreatePostOrReadOnly
)



logger = getLogger(__name__)


def is_rate_limited(request, action_name, limit) -> bool:
    ip = request.META.get('REMOTE_ADDR')
    cache_key = 'rate_limit_%s_%s' % (action_name, ip)
    count = cache.get(cache_key, 0)
    if count >= limit:
        return True
    cache.set(cache_key, count + 1, timeout=60)
    return False


def rate_limit_key(request,exception)->Response:
    """Custom rate limit key function that uses user ID if authenticated, otherwise falls back to IP address"""
   
    logger.warning(
        f"Rate limit exceeded for user: {request.user.id if request.user.is_authenticated else 'Anonymous'}"
        f"from IP: {request.META.get('REMOTE_ADDR')}"
    )
    return Response(
        {
            'detail': 'Rate limit exceeded. Please try again later.'
         },
        status=HTTP_429_TOO_MANY_REQUESTS
    )

def published_comment_event(comment: Comment)->None:
    """Event handler for when a comment is published"""
    try:
        redis_client = cache.client.get_client()

        event_data = {
            'event': 'comment_published',
            'data': {
                'comment_id': comment.id,
                'post_id': comment.post.id,
                'author_id': comment.author.id,
                'content': comment.body,
                'created_at': comment.created_at.isoformat()
            }
        }

        message = json.dumps(event_data, default=str)
        message_published = redis_client.publish('comments', message)

        logger.info(
            f"Published comment event for comment id: {comment.id}, "
            f"post id: {comment.post.id}, "
            f"author id: {comment.author.id}, ")
    except Exception as e:
        logger.error(
            f"Failed to publish comment event for comment id: {comment.id}, "
            f"post id: {comment.post.id}, "
            f"author id: {comment.author.id}, "
            f"error: {str(e)}"
        )


class PostViewSet(ViewSet):
    """
    endpoints:
    GET /api/posts/ — no auth. List published posts (paginated).
    POST /api/posts/ — auth required. Create a new post.
    GET /api/posts/{slug}/ — no auth. Get a single post.
    PATCH /api/posts/{slug}/ — auth required. Update own post.
    DELETE /api/posts/{slug}/ — auth required. Delete own post.
    GET /api/posts/{slug}/comments/ — no auth. List comments for a post.
    POST /api/posts/{slug}/comments/ — auth required. Add a comment.
    """

    lookup_field = 'slug'
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsPublishedOrEdit]
        elif self.action in ['create']:
            permission_classes = [IsCreatePostOrReadOnly]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsPublishedOrEdit]
        elif self.action in ['comments']:
            permission_classes = [IsAddCommentOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def list(self, request):
        
        user_info = (
            f"User_info:{request.user.id} - {request.user.email}"
            if request.user.is_authenticated 
            else "Anonymous User"
        )
        logger.info(f"Post list requested by {user_info}")  

        if request.user.is_authenticated:
            queryset = Post.objects.filter(
                Q(status = Post.Status.PUBLISHED) | Q(author=request.user)
            ).select_related('author').prefetch_related('tags')

            logger.debug(f"Queryset for authenticated user {request.user.email}: {queryset}")
            serializer = PostSerializer(
                queryset, 
                many=True
            )
            return Response(
                {
                    'posts': serializer.data,
                    'total_posts': queryset.count()
                },
                status=HTTP_200_OK
            )
        
        cache_key = 'published_posts'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info("Cache hit for published posts")
            return Response(
                {
                    'posts': cached_data,
                    'total_posts': len(cached_data)
                },
                status=HTTP_200_OK
            )
        logger.info("Cache miss for published posts, querying database")

        queryset = Post.objects.filter(status=Post.Status.PUBLISHED)
        logger.debug(f"Queryset for anonymous user: {queryset.count()} posts found")
        serializer = PostSerializer(
            queryset, 
            many=True
        )
        response_data = serializer.data
        cache.set(cache_key, response_data, timeout=60)
        logger.info("Published posts cached for 60 seconds")

        return Response(

            {
                'posts': response_data,
                'total_posts': queryset.count()
            },
            status=HTTP_200_OK
        )

    def create(
        self, 
        request,
        *args:tuple[Any, ...],
        **kwargs:dict[str, Any]
    )->Response:
        """
        Create a new post
        """

        if is_rate_limited(request, 'create', 20):
            return rate_limit_key(request, None)


        if not request.user.is_authenticated:
            logger.warning("Unauthorized post creation attempt")
            return Response(
                {
                    'error': 'Authentication required to create a post'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        serializer = CreatePostSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            post = serializer.save(author=request.user)

            cache.delete('published_posts')
            logger.info(f"Cache invalidated for published posts after new post creation by {request.user.email}")

            logger.info(f"Post created successfully by user {request.user.email}: {post.title}")
            return Response(
                {
                    'message': 'Post created successfully',
                    'post': PostSerializer(post).data
                },
                status=HTTP_201_CREATED
            )
        logger.warning(
            f"Post creation failed for user {request.user.email}," 
            f"errors: {serializer.errors}")
        return Response(
            serializer.errors,
            status=HTTP_400_BAD_REQUEST
        )
    
    def retrieve(self, request, slug=None)->Response:
        """
        Get a single post
        """


        logger.info(
            f"Post retrieval requested for slug: {slug}"
            f"by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")

        try:
            post = Post.objects.get(slug=slug)
            logger.info(f"Post found: {post.title} (slug: {slug})")
        except Post.DoesNotExist:
            logger.warning(f"Post not found for slug: {slug}")
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        serializer = PostSerializer(post)

        return Response(
            serializer.data, 
            status=HTTP_200_OK
        )
    
    def update(self, request, slug=None)->Response:
        """Update own post"""
        

        if not request.user.is_authenticated:
            logger.warning("Unauthorized post update attempt by anonymous user")
            return Response(
                {
                    'error': 'Authentication required to update a post'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        logger.info(
            f"Post update requested for slug: {slug}"
            f"by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")

        try:
            post = Post.objects.get(slug=slug)
            logger.info(f"Post found for update: {post.title} (slug: {slug})")
        except Post.DoesNotExist:
            logger.warning(f"Post not found for update with slug: {slug}")
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        if post.author != request.user:
            logger.warning(
                f"Unauthorized post update attempt by user {request.user.email}"
                f"on post: {post.title} (slug: {slug})")
            return Response(
                {
                    'error': 'You do not have permission to edit this post'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        
        serializer = EditPostSerializer(
            post, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            updated_post = serializer.save()

            cache.delete('published_posts')
            logger.info(f"Cache invalidated for published posts after post update by {request.user.email}")

            logger.info(f"Post updated successfully by user {request.user.email}: {updated_post.title}")
            return Response(
                {
                    'message': 'Post updated successfully',
                    'post': PostSerializer(updated_post).data
                },
                status=HTTP_200_OK
             )
        logger.warning(f"Post update failed for user {request.user.email}, errors: {serializer.errors}")
        return Response(
            serializer.errors,
            status=HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, slug=None)->Response:
        """Delete own post"""
    

        if not request.user.is_authenticated:
            logger.warning("Unauthorized post deletion attempt by anonymous user")
            return Response(
                {
                    'error': 'Authentication required to delete a post'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        logger.info(
            f"Post deletion requested for slug: {slug}"
            f"by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}"
        )

        try:
            post = Post.objects.get(slug=slug)
            logger.info(f"Post found for deletion: {post.title} (slug: {slug})")
        except Post.DoesNotExist:
            logger.warning(f"Post not found for deletion with slug: {slug}")
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        post.delete()

        cache.delete('published_posts')
        logger.info(f"Cache invalidated for published posts after post deletion by {request.user.email}")

        logger.info(f"Post deleted successfully by user {request.user.email}: {post.title}")
        return Response(
            {
                'message': 'Post deleted successfully'
            },
             status=HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, slug=None)->Response:
        """LIst comments for a post or add a comment"""


        logger.info(
            f"Comments endpoint accessed for post slug: {slug}"
            f"by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")

        try:
            post = Post.objects.get(slug=slug)
            logger.info(f"Post found for comments: {post.title} (slug: {slug})")
        except Post.DoesNotExist:
            logger.warning(f"Post not found for comments with slug: {slug}")
            return Response(
                {
                    'error': 'Post not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        if request.method == 'GET':
            logger.info(f"Listing comments for post: {post.title} (slug: {slug})")

            comments = post.comments.all().order_by('-created_at')

            serializer = CommentSerializer(
                comments,
                many=True
            )
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
            serializer = CommentSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                comment = serializer.save(author=request.user, post=post)

                published_comment_event(comment)

                logger.info(
                    f"Comment added successfully by user {request.user.email}"
                    f"to post: {post.title} (slug: {slug})")
                return Response(
                    {
                        'message': 'Comment added successfully',
                        'comment': CommentSerializer(comment).data
                    },
                    status=HTTP_201_CREATED
                 )
            logger.error(
                f"Comment creation failed for user {request.user.email}"
                f"on post: {post.title} (slug: {slug}), errors: {serializer.errors}")
            return Response(
                serializer.errors,
                status=HTTP_400_BAD_REQUEST
            )
        

class CommentViewSet(ViewSet):
    """
    endpoints:
    GET /api/comments/{id}/ — no auth. Get a single comment.
    PATCH /api/comments/{id}/ — auth required. Update own comment.
    DELETE /api/comments/{id}/ — auth required. Delete own comment.
    """

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            permission_classes = [IsAddCommentOrReadOnly]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAddCommentOrReadOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def list(self, request)->Response:
        """List comments - not implemented as comments are accessed via posts"""


        queryset = Comment.objects.all().order_by('-created_at')
        logger.info(f"Listing all comments, total count: {queryset.count()}")

        serializer = CommentSerializer(
            queryset,
            many=True
        )
        return Response(
            serializer.data,
            status=HTTP_200_OK
        )
    
    def retrieve(self, request, pk=None)->Response:
        """Get a single comment"""
       

        logger.info(
            f"Comment retrieval requested for id: {pk}"
            f"by user: {request.user.email if request.user.is_authenticated 
            else 'Anonymous'}"
        )

        try:
            comment = Comment.objects.get(pk=pk)
            logger.info(f"Comment found: {comment.id} for post: {comment.post.title}")
        except Comment.DoesNotExist:
            logger.warning(f"Comment not found for id: {pk}")
            return Response(
                {
                    'error': 'Comment not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        serializer = CommentSerializer(comment)

        return Response(
            serializer.data, 
            status=HTTP_200_OK
        )
    
    def destroy(self, request, pk=None)->Response:
        """Delete own comment"""
        

        if not request.user.is_authenticated:
            logger.warning("Unauthorized comment deletion attempt by anonymous user")
            return Response(
                {
                    'error': 'Authentication required to delete a comment'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        logger.info(
            f"Comment deletion requested for id: {pk}"
            f"by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}"
        )

        try:
            comment = Comment.objects.get(pk=pk)
            logger.info(f"Comment found for deletion: {comment.id} for post: {comment.post.title}")
        except Comment.DoesNotExist:
            logger.warning(f"Comment not found for deletion with id: {pk}")
            return Response(
                {
                    'error': 'Comment not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        if comment.author != request.user:
            logger.warning(
                f"Unauthorized comment deletion attempt by user {request.user.email}"
                f"on comment id: {comment.id}"
            )
            
            return Response(
                {
                    'error': 'You do not have permission to delete this comment'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        
        comment.delete()
        logger.info(f"Comment deleted successfully by user {request.user.email} on comment id: {comment.id} for post: {comment.post.title}")
        return Response(
            {
                'message': 'Comment deleted successfully'
            },
             status=HTTP_204_NO_CONTENT
        )


    def partial_update(self, request, pk=None)->Response:
        """Update own comment"""
        

        if not request.user.is_authenticated:
            logger.warning("Unauthorized comment update attempt by anonymous user")
            return Response(
                {
                    'error': 'Authentication required to update a comment'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        logger.info(
            f"Comment update requested for id: {pk}"
            f"by user:{request.user.email if request.user.is_authenticated else 'Anonymous'}"
        )

        try:
            comment = Comment.objects.get(pk=pk)
            logger.info(f"Comment found for update: {comment.id} for post: {comment.post.title}")
        except Comment.DoesNotExist:
            logger.warning(f"Comment not found for update with id: {pk}")
            return Response(
                {
                    'error': 'Comment not found'
                },
                status=HTTP_404_NOT_FOUND
            )
        
        if comment.author != request.user:
            logger.warning(
                f"Unauthorized comment update attempt by user {request.user.email}"
                f"on comment id: {comment.id}"
            )
            
            return Response(
                {
                    'error': 'You do not have permission to edit this comment'
                },
                status=HTTP_401_UNAUTHORIZED
            )
        
        serializer = EditCommentSerializer(
            comment, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            updated_comment = serializer.save()
            logger.info(
                f"Comment updated successfully by user {request.user.email}"
                f"on comment id: {updated_comment.id}")
            return Response(
                {
                    'message': 'Comment updated successfully',
                    'comment': CommentSerializer(updated_comment).data
                },
                status=HTTP_200_OK
             )
        logger.warning(
            f"Comment update failed for user {request.user.email}"
            f"on comment id: {comment.id}, errors: {serializer.errors}")
        return Response(
            serializer.errors,
            status=HTTP_400_BAD_REQUEST
        )