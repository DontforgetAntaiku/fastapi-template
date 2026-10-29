import datetime as dt

import pytest
from pydantic import ValidationError

from app.database.filters import FilterSet, filterset_for
from app.database.models import User
from tests.models import HiddenNote


def test_auto_filter_covers_columns_but_never_private_ones():
    fields = set(User.get_filter_model().model_fields)
    assert {
        "username__icontains",
        "telegram_id__in",
        "created_at__gte",
        "is_active",
    } <= fields
    assert {"id", "id__in", "username__isnull"} <= fields
    assert not any("password" in name for name in fields)


def test_auto_filter_skips_sensitive_looking_columns():
    fields = set(filterset_for(HiddenNote).model_fields)
    assert "title" in fields
    assert not any(name.startswith("secret_code") for name in fields)
    assert (
        "secret_code"
        in filterset_for(HiddenNote, fields={"secret_code": ["exact"]}).model_fields
    )


def test_explicit_fields_are_validated_at_build_time():
    with pytest.raises(ValueError, match="not a filterable column"):
        filterset_for(User, fields={"nope": ["exact"]})
    with pytest.raises(ValueError, match="private"):
        filterset_for(User, fields={"password_hash": ["exact"]})
    with pytest.raises(ValueError, match="not valid for int"):
        filterset_for(User, fields={"telegram_id": ["icontains"]})
    with pytest.raises(ValueError, match="cannot sort"):
        filterset_for(User, sort=["nope"])


def test_generated_class_is_a_strict_filterset():
    Filter = User.get_filter_model(default_limit=10, max_limit=20)
    assert issubclass(Filter, FilterSet) and Filter.__name__ == "UserFilter"
    assert Filter().limit == 10
    with pytest.raises(ValidationError):
        Filter(limit=21)
    with pytest.raises(ValidationError):
        Filter(unknown="x")
    with pytest.raises(ValidationError):
        Filter(sort="password_hash")
    with pytest.raises(ValidationError):
        Filter(username__in=["x"] * 101)
    with pytest.raises(ValidationError):
        Filter(username="x" * 65)


async def test_apply_filters_sorts_and_pages(db):
    base = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    for i, name in enumerate(["alice", "alina", "bob", "carol"]):
        await User.create(
            username=name, first_name=name, telegram_id=i, is_admin=i == 3
        )
    Filter = User.get_filter_model()

    async def names(**kwargs):
        users = await Filter(**kwargs).apply(User.all())
        return [u.username for u in users]

    assert await names(username__istartswith="ali", sort="-username") == [
        "alina",
        "alice",
    ]
    assert await names(telegram_id__in=[0, 2]) == ["alice", "bob"]
    assert await names(telegram_id__gte=2, sort="-telegram_id") == ["carol", "bob"]
    assert await names(is_admin=True) == ["carol"]
    assert await names(is_admin=False, limit=2, offset=1) == ["alina", "bob"]
    assert await names(created_at__gte=base) == ["alice", "alina", "bob", "carol"]
    assert await names(last_name__isnull=True, limit=1) == ["alice"]
    assert await names(telegram_id=0) == ["alice"]
    assert (
        await Filter(username__icontains="ali").apply_filters(User.all()).count() == 2
    )
