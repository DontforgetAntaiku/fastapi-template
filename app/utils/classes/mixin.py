from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.manager import Manager
from tortoise.models import Model
from tortoise.queryset import QuerySet


class PydanticMixin:
    private_fields: ClassVar[tuple[str, ...]] = ()
    _pydantic_cache: ClassVar[dict[str, type[BaseModel]]]

    @classmethod
    def _schema(cls, key: str, **kwargs: Any) -> type[BaseModel]:
        if "_pydantic_cache" not in cls.__dict__:
            cls._pydantic_cache = {}
        if key not in cls._pydantic_cache:
            cls._pydantic_cache[key] = pydantic_model_creator(
                cls,  # type: ignore[arg-type]
                name=f"{cls.__name__}{key}",
                exclude=cls.private_fields,
                **kwargs,
            )
        return cls._pydantic_cache[key]

    @classmethod
    def get_pydantic_model(cls) -> type[BaseModel]:
        return cls._schema("")

    @classmethod
    def get_input_model(cls) -> type[BaseModel]:
        return cls._schema("In", exclude_readonly=True)

    @classmethod
    def get_update_model(cls) -> type[BaseModel]:
        return cls._schema(
            "Update",
            exclude_readonly=True,
            optional=tuple(cls.get_input_model().model_fields),
        )

    async def to_pydantic(self) -> BaseModel:
        schema = self.__class__.get_pydantic_model()
        return await schema.from_tortoise_orm(self)  # type: ignore[attr-defined]

    async def to_dict(self) -> dict:
        return (await self.to_pydantic()).model_dump()

    async def to_json(self) -> str:
        return (await self.to_pydantic()).model_dump_json()


class SoftDeleteManager(Manager):
    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(deleted_at=None)


class SoftDeleteMixin(Model):
    deleted_at = fields.DatetimeField(null=True, db_index=True)

    class Meta:  # pyright: ignore
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    async def soft_delete(self) -> None:
        self.deleted_at = datetime.now(UTC)
        await self.save(update_fields=self._stamp_fields())

    async def restore(self) -> None:
        self.deleted_at = None
        await self.save(update_fields=self._stamp_fields())

    def _stamp_fields(self) -> list[str]:
        names = ["deleted_at"]
        if "updated_at" in self._meta.fields_map:
            names.append("updated_at")
        return names

    @classmethod
    def alive(cls) -> QuerySet:
        return QuerySet(cls).filter(deleted_at=None)

    @classmethod
    def only_deleted(cls) -> QuerySet:
        return QuerySet(cls).filter(deleted_at__isnull=False)
