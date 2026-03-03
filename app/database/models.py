from tortoise import fields
from tortoise.models import Model

from app.utils.classes.mixin import PydanticMixin


class User(Model, PydanticMixin):
    id = fields.BigIntField(primary_key=True)
    username = fields.CharField(max_length=255, null=True)
    first_name = fields.CharField(max_length=255, null=False)
    last_name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:  # pyright: ignore
        table = "users"
