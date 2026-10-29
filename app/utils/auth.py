import asyncio
import hashlib
import hmac
import json
import secrets
from typing import Annotated
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.core.dependencies import RedisDep, SettingsDep
from app.core.settings import Settings
from app.database.models import User

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "QUERY"})
CSRF_HEADER = "X-CSRF-Token"

_hasher = PasswordHasher()
_DUMMY_HASH = _hasher.hash("timing-equalizer")


def _verify(password_hash: str | None, password: str) -> tuple[bool, bool]:
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except VerificationError, InvalidHashError:
        return False, False
    if password_hash is None:
        return False, False
    return True, _hasher.check_needs_rehash(password_hash)


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(
    password_hash: str | None, password: str
) -> tuple[bool, bool]:
    return await asyncio.to_thread(_verify, password_hash, password)


def _key(sid: str) -> str:
    return f"sess:{sid}"


async def create_session(
    request: Request, redis: Redis, user: User, settings: Settings
) -> str:
    await destroy_session(request, redis)
    sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    payload = json.dumps({"user_id": str(user.id), "csrf": csrf})
    await redis.set(_key(sid), payload, ex=settings.app.SESSION_TTL)
    request.session["sid"] = sid
    return csrf


async def destroy_session(request: Request, redis: Redis) -> None:
    sid = request.session.pop("sid", None)
    if sid:
        await redis.delete(_key(sid))


async def _load_session(request: Request, redis: Redis) -> dict | None:
    sid = request.session.get("sid")
    raw = await redis.get(_key(sid)) if isinstance(sid, str) else None
    return json.loads(raw) if raw else None


def verify_origin(request: Request, settings: SettingsDep) -> None:
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is None:
        return
    if origin in settings.app.ORIGINS:
        return
    if urlsplit(origin).netloc == request.headers.get("host"):
        return
    raise HTTPException(status_code=403, detail="Origin not allowed")


async def require_user(
    request: Request,
    redis: RedisDep,
    _: Annotated[None, Depends(verify_origin)],
) -> User:
    data = await _load_session(request, redis)
    if data is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if request.method not in SAFE_METHODS:
        supplied = request.headers.get(CSRF_HEADER, "").encode()
        if not hmac.compare_digest(supplied, data["csrf"].encode()):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    user = await User.get_or_none(id=data["user_id"])
    if user is None or not user.is_active:
        await destroy_session(request, redis)
        raise HTTPException(status_code=401, detail="Not authenticated")
    request.state.csrf_token = data["csrf"]
    return user


async def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


CurrentUser = Annotated[User, Depends(require_user)]
AdminUser = Annotated[User, Depends(require_admin)]


def identifier(value: str, settings: Settings) -> str:
    secret = settings.app.LOGIN_SECRET.get_secret_value().encode()
    return hmac.new(secret, value.lower().encode(), hashlib.sha256).hexdigest()[:32]
