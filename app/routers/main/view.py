import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from tortoise import connections

from app.core.dependencies import RedisDep

router = APIRouter()
logger = logging.getLogger(__name__)

CHECK_TIMEOUT = 2.0


@router.get("/health")
async def health():
    return {"status": "ok"}


async def _check(name: str, probe: Callable[[], Awaitable[object]]) -> str:
    try:
        await asyncio.wait_for(probe(), CHECK_TIMEOUT)
    except Exception:
        logger.warning("readiness check failed: %s", name, exc_info=True)
        return "error"
    return "ok"


@router.get("/ready")
async def ready(redis: RedisDep):
    checks = {
        "database": await _check(
            "database", lambda: connections.get("default").execute_query("SELECT 1")
        ),
        "redis": await _check("redis", redis.ping),
    }
    healthy = all(result == "ok" for result in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "unavailable", "checks": checks},
        status_code=200 if healthy else 503,
    )
