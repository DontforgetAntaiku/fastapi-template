from fastapi import APIRouter, Depends

from app.utils.auth import verify_origin
from app.utils.ratelimit import rate_limit
from app.utils.schemas.auth import RegisterIn
from app.utils.schemas.user import UserOut
from app.utils.services.auth import register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(verify_origin), Depends(rate_limit("5/hour", "register"))],
)
async def register(payload: RegisterIn):
    user = await register_user(payload)
    return await user.to_pydantic()
