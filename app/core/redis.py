from fastapi import Request
from redis.asyncio import Redis

from .settings import Settings


def create_redis(settings: Settings) -> Redis:
    password = settings.redis.PASSWORD
    return Redis(
        host=settings.redis.HOST,
        port=settings.redis.PORT,
        db=settings.redis.DB,
        password=password.get_secret_value() if password else None,
        decode_responses=True,
    )


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
