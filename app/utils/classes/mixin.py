from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator


class PydanticMixin:
    _pydantic_schema: ClassVar[type[BaseModel] | None] = None

    @classmethod
    def get_pydantic_model(cls) -> type[BaseModel]:
        if cls._pydantic_schema is None:
            cls._pydantic_schema = pydantic_model_creator(cls)  # type: ignore[arg-type]
        return cls._pydantic_schema

    async def to_pydantic(self) -> BaseModel:
        schema = self.__class__.get_pydantic_model()
        return await schema.from_tortoise_orm(self)  # type: ignore[arg-type]

    async def to_dict(self) -> dict:
        return (await self.to_pydantic()).model_dump()

    async def to_json(self) -> str:
        return (await self.to_pydantic()).model_dump_json()
