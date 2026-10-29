from fastapi import HTTPException, Request
from redis.asyncio import Redis

from app.core.settings import Settings
from app.database.models import User
from app.utils.auth import (
    create_session,
    hash_password,
    identifier,
    verify_password,
)
from app.utils.dataclasses.telegram import TelegramUser
from app.utils.exceptions.telegram import TelegramAuthError
from app.utils.ratelimit import FailureThrottle, client_id
from app.utils.schemas.auth import AuthOut, LoginIn, RegisterIn, WebAppIn, WidgetIn
from app.utils.telegram import verify_init_data, verify_widget

login_throttle = FailureThrottle("login", "5/15min")


async def auth_response(user: User, csrf_token: str) -> AuthOut:
    return AuthOut(user=await user.to_pydantic(), csrf_token=csrf_token)


async def password_login(
    request: Request, payload: LoginIn, redis: Redis, settings: Settings
) -> AuthOut:
    who = identifier(payload.username, settings)
    ip = client_id(request, settings)
    await login_throttle.check(redis, ip, who)

    user = await User.get_or_none(username=payload.username)
    valid, needs_rehash = await verify_password(
        user.password_hash if user else None, payload.password
    )
    if user is None or not valid or not user.is_active:
        await login_throttle.fail(redis, ip, who)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # clear only the username counter, or a valid account could reset its own IP counter
    await login_throttle.clear(redis, who)
    if needs_rehash:
        user.password_hash = await hash_password(payload.password)
        await user.save(update_fields=["password_hash"])
    csrf = await create_session(request, redis, user, settings)
    return await auth_response(user, csrf)


async def register_user(payload: RegisterIn) -> User:
    return await User.create(
        username=payload.username,
        first_name=payload.first_name,
        password_hash=await hash_password(payload.password),
    )


def _bot_token(settings: Settings) -> str:
    token = settings.app.TELEGRAM_BOT_TOKEN
    if token is None:
        raise HTTPException(status_code=404, detail="Not found")
    return token.get_secret_value()


async def _telegram_sign_in(
    tg: TelegramUser, request: Request, redis: Redis, settings: Settings
) -> AuthOut:
    user = await User.get_or_none(telegram_id=tg.id)
    if user is None:
        user = await User.create(
            telegram_id=tg.id, first_name=tg.first_name, last_name=tg.last_name
        )
    elif (user.first_name, user.last_name) != (tg.first_name, tg.last_name):
        user.first_name, user.last_name = tg.first_name, tg.last_name
        await user.save(update_fields=["first_name", "last_name"])
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    csrf = await create_session(request, redis, user, settings)
    return await auth_response(user, csrf)


async def telegram_webapp_login(
    request: Request, payload: WebAppIn, redis: Redis, settings: Settings
) -> AuthOut:
    try:
        tg = verify_init_data(
            payload.init_data, _bot_token(settings), settings.app.TELEGRAM_AUTH_MAX_AGE
        )
    except TelegramAuthError:
        raise HTTPException(status_code=401, detail="Invalid Telegram login") from None
    return await _telegram_sign_in(tg, request, redis, settings)


async def telegram_widget_login(
    request: Request, payload: WidgetIn, redis: Redis, settings: Settings
) -> AuthOut:
    fields = {k: str(v) for k, v in payload.model_dump(exclude_none=True).items()}
    try:
        tg = verify_widget(
            fields, _bot_token(settings), settings.app.TELEGRAM_AUTH_MAX_AGE
        )
    except TelegramAuthError:
        raise HTTPException(status_code=401, detail="Invalid Telegram login") from None
    return await _telegram_sign_in(tg, request, redis, settings)
