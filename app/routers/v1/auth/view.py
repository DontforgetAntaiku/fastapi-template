from fastapi import APIRouter, Depends, Request

from app.core.dependencies import RedisDep, SettingsDep
from app.utils.auth import CurrentUser, destroy_session, verify_origin
from app.utils.ratelimit import rate_limit
from app.utils.schemas.auth import AuthOut, LoginIn
from app.utils.services.auth import auth_response, password_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=AuthOut,
    dependencies=[Depends(verify_origin), Depends(rate_limit("30/minute", "login"))],
)
async def login(
    request: Request, payload: LoginIn, redis: RedisDep, settings: SettingsDep
):
    return await password_login(request, payload, redis, settings)


@router.post("/logout", status_code=204)
async def logout(request: Request, user: CurrentUser, redis: RedisDep):
    await destroy_session(request, redis)


@router.get("/me", response_model=AuthOut)
async def me(request: Request, user: CurrentUser):
    return await auth_response(user, request.state.csrf_token)
