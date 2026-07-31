import logging
import os
from typing import Final

from redis.asyncio import Redis

from app.utils.classes.config import Config

DEBUG = True


LOG_LEVEL: Final[int] = logging.ERROR
WORK_DIR: Final[str] = os.path.dirname(__file__)

CONFIG: Final = Config(".env")

REDIS: Redis = Redis(
    host=CONFIG.redis.HOST,
    port=CONFIG.redis.PORT,
    db=CONFIG.redis.DB or 0,
    password=CONFIG.redis.PASSWORD,
)
