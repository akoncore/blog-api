import json 

#Django modules
from django.contrib.auth import get_user_model

#Rest framework modules
from rest_framework_simplejwt.tokens import AccessToken

#Channels modules
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

#Project modules
from apps.blog.models import Post

User = get_user_model()

class CommentConsumer(AsyncWebsocketConsumer):
    """
    Consumer for handling WebSocket connections related to comments on blog posts.
    """

    async def connect(self):
        """
        Handles the WebSocket connection when a client connects.
        """
        self.post_slug = self.scope["url_route"]["kwargs"]["post_slug"]
        self.group_name = f"comments_{self.post_slug}"

        #Jwt authentication
        user = await self._authenticate_user()
        if user is None:
            await self.close_code(4001)  # Close with an error code for unauthorized access
            return
        
        #Post existence check
        exists = await self._post_exists()
        if not exists:
            await self.close_code(4004)  # Close with an error code for post not found
            return
        
        #Group addition
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, code):
        """
        Handles the WebSocket disconnection when a client disconnects.
        """
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def comment_message(self, event):
        """
        handles the reception of a comment message and sends it to the WebSocket client.
        """
        await self.send(
            text_data=json.dumps(event["meassage"])
        )

    #authentication and post existence check methods
    async def _authenticate_user(self):
        """
        Atuhenticates the user using JWT token from the query parameters.
        """

        token = self.scope["query_string"].decode()
        params = dict(
            params.split("=") for params in token.split("&") if "=" in params
        )

        jwt_token = params.get("token")
        if jwt_token is None:
            return None
        try:
            accesc_token = AccessToken(jwt_token)
            user = await database_sync_to_async(
                User.objects.get(id=accesc_token["user_id"])
            )
            return user
        except Exception as e:
            return None
    
    #Post existence check method
    @database_sync_to_async
    def _post_exists(self):
        """
        Checks if the post with the given slug exists in the database.
        """
        return Post.objects.filter(
            slug=self.post_slug
        ).exists()
        