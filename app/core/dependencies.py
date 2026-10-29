from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.redis import get_redis
from app.core.settings import Settings, get_settings

RedisDep = Annotated[Redis, Depends(get_redis)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
