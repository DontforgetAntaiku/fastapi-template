import hashlib
import hmac
import re
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.dependencies import RedisDep, SettingsDep
from app.core.settings import Settings

_UNITS = {"s": 1, "sec": 1, "second": 1, "m": 60, "min": 60, "minute": 60,
          "h": 3600, "hour": 3600, "d": 86400, "day": 86400}  # fmt: skip
_SPEC = re.compile(r"^(\d+)/(\d+)?([a-z]+?)s?$")


def parse_rate(spec: str) -> tuple[int, int]:
    match = _SPEC.match(spec.strip().lower())
    if not match or match.group(3) not in _UNITS:
        raise ValueError(
            f"bad rate limit {spec!r}, expected e.g. '5/minute', '10/15min'"
        )
    limit, multiplier, unit = match.groups()
    return int(limit), int(multiplier or 1) * _UNITS[unit]


def client_id(request: Request, settings: Settings) -> str:
    ip = request.client.host if request.client else "unknown"
    secret = settings.app.LOGIN_SECRET.get_secret_value().encode()
    return hmac.new(secret, ip.encode(), hashlib.sha256).hexdigest()[:32]


async def _incr(redis: Redis, key: str, window: int) -> tuple[int, int]:
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        pipe.ttl(key)
        count, _, ttl = await pipe.execute()
    return int(count), max(int(ttl), 1)


def rate_limit(spec: str, scope: str | None = None) -> Callable[..., Awaitable[None]]:
    limit, window = parse_rate(spec)

    async def dependency(
        request: Request,
        redis: RedisDep,
        settings: SettingsDep,
    ) -> None:
        route = request.scope.get("route")
        name = scope or getattr(route, "path", request.url.path)
        key = f"rl:{name}:{client_id(request, settings)}"
        count, ttl = await _incr(redis, key, window)
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(ttl)},
            )

    return dependency


class FailureThrottle:
    def __init__(self, scope: str, spec: str) -> None:
        self.scope = scope
        self.limit, self.window = parse_rate(spec)

    def _key(self, identifier: str) -> str:
        return f"thr:{self.scope}:{identifier}"

    async def check(self, redis: Redis, *identifiers: str) -> None:
        for identifier in identifiers:
            count = int(await redis.get(self._key(identifier)) or 0)
            if count >= self.limit:
                ttl = max(int(await redis.ttl(self._key(identifier))), 1)
                raise HTTPException(
                    status_code=429,
                    detail="Too many failed attempts",
                    headers={"Retry-After": str(ttl)},
                )

    async def fail(self, redis: Redis, *identifiers: str) -> None:
        for identifier in identifiers:
            await _incr(redis, self._key(identifier), self.window)

    async def clear(self, redis: Redis, *identifiers: str) -> None:
        if identifiers:
            await redis.delete(*(self._key(i) for i in identifiers))
