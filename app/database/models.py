from tortoise import fields

from app.database.base import AppModel


class User(AppModel):
    telegram_id = fields.BigIntField(unique=True, null=True)
    username = fields.CharField(max_length=64, unique=True, null=True)
    first_name = fields.CharField(max_length=255, null=False)
    last_name = fields.CharField(max_length=255, null=True)
    password_hash = fields.CharField(max_length=255, null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)

    private_fields = ("password_hash",)

    class Meta:  # pyright: ignore
        table = "users"
