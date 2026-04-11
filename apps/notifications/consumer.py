import json 
from urllib.parse import parse_qs

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
            await self.close(code=4001)  # Close with an error code for unauthorized access
            return
        
        #Post existence check
        exists = await self._post_exists()
        if not exists:
            await self.close(code=4004)  # Close with an error code for post not found
            return
        
        #Group addition
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    #WebSocket disconnection handler
    async def disconnect(self, code):
        """
        Handles the WebSocket disconnection when a client disconnects.
        """
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    #Message handler for receiving comment messages
    async def comment_message(self, event):
        """
        handles the reception of a comment message and sends it to the WebSocket client.
        """
        await self.send(
            text_data=json.dumps(event.get("message", {}))
        )

    #authentication and post existence check methods
    async def _authenticate_user(self):
        """
        Atuhenticates the user using JWT token from the query parameters.
        """

        try:
            token = self.scope.get("query_string", b'').decode('utf-8')
            params = parse_qs(token)

            jwt_list = params.get("token",None)
            jwt_token = jwt_list[0]

            if not jwt_token:
                return None
            
            access_token = AccessToken(jwt_token)
            user_id = access_token['user_id']

            user = await database_sync_to_async(User.objects.get)(id=user_id)
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
        