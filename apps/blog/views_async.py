import asyncio
import logging

import httpx

from adrf.views import APIView

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from apps.blog.models import Post, Comment


logger = logging.getLogger(__name__)


class StasView(APIView):
    """
    Async view for /api/stats/
    """

    permission_classes = [AllowAny]

    async def get(self, request):
            async with httpx.AsyncClient(timeout=10.0) as client:
                  rates_resp, time_resp = await asyncio.gather(
                        client.get("https://open.er-api.com/v6/latest/USD"),
                        client.get("https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty")
                  )

            total_post = await Post.objects.acount()
            total_comment = await Comment.objects.acount()
            total_users = await get_user_model().objects.acount()

            rates = rates_resp.json().get("rates",{})
            current_time = time_resp.json().get("dateTime","")

            logger.info('Stats endpoints called: external APIs fetched concurrently')

            return Response({
                "Blog":{
                        "total_posts":total_post,
                        "total_comment":total_comment,
                        "total_users":total_users
                },
                "exchange_rates":{
                        "KZT":rates.get("KZT"),
                        "RUB":rates.get("RUB"),
                        "EUR":rates.get("RUB")
                },
                "current_time":current_time
                }
            )