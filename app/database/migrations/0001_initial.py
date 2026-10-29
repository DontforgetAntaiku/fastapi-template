from tortoise import migrations
from tortoise.migrations import operations as ops
from uuid import uuid7
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid7, unique=True, db_index=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('telegram_id', fields.BigIntField(null=True, unique=True)),
                ('username', fields.CharField(null=True, unique=True, max_length=64)),
                ('first_name', fields.CharField(max_length=255)),
                ('last_name', fields.CharField(null=True, max_length=255)),
                ('password_hash', fields.CharField(null=True, max_length=255)),
                ('is_active', fields.BooleanField(default=True)),
                ('is_admin', fields.BooleanField(default=False)),
            ],
            options={'table': 'users', 'app': 'models', 'pk_attr': 'id'},
            bases=['AppModel'],
        ),
    ]
