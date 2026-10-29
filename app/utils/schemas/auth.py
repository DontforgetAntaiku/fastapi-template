from pydantic import BaseModel, ConfigDict, Field

from app.utils.schemas.user import UserOut


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=255)


class AuthOut(BaseModel):
    user: UserOut
    csrf_token: str


class WebAppIn(BaseModel):
    init_data: str = Field(min_length=1, max_length=4096)


class WidgetIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str = Field(max_length=255)
    auth_date: int
    hash: str = Field(max_length=64)
