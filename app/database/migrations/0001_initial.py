from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.BigIntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('username', fields.CharField(null=True, max_length=255)),
                ('first_name', fields.CharField(max_length=255)),
                ('last_name', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'users', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model', 'PydanticMixin'],
        ),
    ]
