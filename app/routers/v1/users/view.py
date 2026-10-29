from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query

from app.database.filters.users import UserFilter
from app.database.models import User
from app.utils.auth import require_admin, require_user
from app.utils.routing import QueryRouter
from app.utils.schemas.user import UserIn, UserOut, UserUpdate

router = QueryRouter(prefix="/users", tags=["users"])

reader = [Depends(require_user)]
writer = [Depends(require_admin)]


async def _find(filters: UserFilter) -> list:
    users = await filters.apply(User.all())
    return [await user.to_pydantic() for user in users]


@router.get("", response_model=list[UserOut], dependencies=reader)
async def list_users(filters: Annotated[UserFilter, Query()]):
    return await _find(filters)


@router.query("", response_model=list[UserOut], dependencies=reader)
async def search_users(filters: UserFilter):
    return await _find(filters)


@router.post("", response_model=UserOut, status_code=201, dependencies=writer)
async def create_user(payload: UserIn):
    user = await User.create(**payload.model_dump())
    return await user.to_pydantic()


@router.get("/{user_id}", response_model=UserOut, dependencies=reader)
async def get_user(user_id: UUID):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return await user.to_pydantic()


@router.patch("/{user_id}", response_model=UserOut, dependencies=writer)
async def update_user(user_id: UUID, payload: UserUpdate):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await user.update_from_dict(payload.model_dump(exclude_unset=True)).save()
    return await user.to_pydantic()


@router.delete("/{user_id}", status_code=204, dependencies=writer)
async def delete_user(user_id: UUID):
    if not await User.filter(id=user_id).delete():
        raise HTTPException(status_code=404, detail="User not found")
