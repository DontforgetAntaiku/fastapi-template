from app.database.filters.generator import filterset_for
from app.database.models import User

UserFilter = filterset_for(
    User,
    name="UserFilter",
    fields={
        "telegram_id": ["exact", "in"],
        "username": ["exact", "icontains"],
        "first_name": ["icontains"],
        "is_active": ["exact"],
        "is_admin": ["exact"],
        "created_at": ["gte", "lte"],
    },
    sort=["created_at", "username", "id"],
)
