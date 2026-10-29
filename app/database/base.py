import uuid
from typing import Any

from tortoise import fields
from tortoise.models import Model

from app.database.filters import FilterSet, filterset_for
from app.utils.classes.mixin import PydanticMixin


class AppModel(Model, PydanticMixin):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid7)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:  # pyright: ignore
        abstract = True

    @classmethod
    def get_filter_model(cls, **options: Any) -> type[FilterSet]:
        return filterset_for(cls, **options)
