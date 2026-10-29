from fastapi import APIRouter

from app.core.settings import Settings

from .auth.view import router as auth
from .users.view import router as users


def build_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/v1")
    router.include_router(auth)
    router.include_router(users)
    if settings.app.ALLOW_REGISTRATION:
        from .auth.register import router as register

        router.include_router(register)
    if settings.app.TELEGRAM_BOT_TOKEN is not None:
        from .auth.telegram import router as telegram

        router.include_router(telegram)
    return router


__all__ = ["build_router"]
