from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsPublishedOrEdit(BasePermission):
    """
    Custom permission to only allow authors of a post to edit it, and allow anyone to view published posts.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request if the post is published
        if request.method in SAFE_METHODS:
            return obj.is_published 
        
        # Write permissions are only allowed to the author of the post
        return obj.author == request.user
    

class IsAddCommentOrReadOnly(BasePermission):
    """
    Custom permission to only allow authenticated users to add comments, and allow anyone to view comments.
    """
    def has_permission(self, request, view):
        # Allow anyone to view comments
        if request.method in SAFE_METHODS:
            return True
        
        # Only allow authenticated users to add comments
        return request.user and request.user.is_authenticated
    
class IsCreatePostOrReadOnly(BasePermission):
    """
    Custom permission to only allow authenticated users to create posts, and allow anyone to view posts.
    """
    def has_permission(self, request, view):
        # Allow anyone to view posts
        if request.method in SAFE_METHODS:
            return True
        
        # Only allow authenticated users to create posts
        return request.user and request.user.is_authenticated