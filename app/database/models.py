from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.BigIntField(primary_key=True)
    username = fields.CharField(max_length=255, null=True)
    first_name = fields.CharField(max_length=255, null=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
