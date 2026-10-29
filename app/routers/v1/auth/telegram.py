from fastapi import APIRouter, Depends, Request

from app.core.dependencies import RedisDep, SettingsDep
from app.utils.auth import verify_origin
from app.utils.ratelimit import rate_limit
from app.utils.schemas.auth import AuthOut, WebAppIn, WidgetIn
from app.utils.services.auth import telegram_webapp_login, telegram_widget_login

router = APIRouter(
    prefix="/auth/telegram",
    tags=["auth"],
    dependencies=[Depends(verify_origin), Depends(rate_limit("20/minute", "telegram"))],
)


@router.post("/webapp", response_model=AuthOut)
async def telegram_webapp(
    request: Request, payload: WebAppIn, redis: RedisDep, settings: SettingsDep
):
    return await telegram_webapp_login(request, payload, redis, settings)


@router.post("/widget", response_model=AuthOut)
async def telegram_widget(
    request: Request, payload: WidgetIn, redis: RedisDep, settings: SettingsDep
):
    return await telegram_widget_login(request, payload, redis, settings)
