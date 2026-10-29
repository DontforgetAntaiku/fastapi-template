import asyncio

from app.database.models import User
from tests.models import HiddenNote, Note


async def test_ids_are_uuid7_and_sort_by_creation(db):
    first = await User.create(first_name="a")
    second = await User.create(first_name="b")
    assert first.id.version == 7
    assert first.id < second.id


async def test_updated_at_moves_on_save_created_at_does_not(db):
    user = await User.create(first_name="a")
    created, updated = user.created_at, user.updated_at
    await asyncio.sleep(0.01)
    user.first_name = "b"
    await user.save()
    assert user.created_at == created
    assert user.updated_at > updated


async def test_pydantic_cache_is_per_class(db):
    assert Note.get_pydantic_model() is not User.get_pydantic_model()
    assert {"title", "deleted_at"} <= set(Note.get_pydantic_model().model_fields)
    assert "deleted_at" not in User.get_pydantic_model().model_fields


async def test_soft_delete_and_restore(db):
    keep = await Note.create(title="keep")
    gone = await Note.create(title="gone")
    assert not gone.is_deleted

    await gone.soft_delete()
    assert gone.is_deleted
    assert [n.title for n in await Note.alive()] == ["keep"]
    assert [n.title for n in await Note.only_deleted()] == ["gone"]
    assert await Note.all().count() == 2

    await gone.restore()
    assert {n.title for n in await Note.alive()} == {"keep", "gone"}
    assert keep.deleted_at is None


async def test_soft_delete_bumps_updated_at(db):
    note = await Note.create(title="t")
    before = note.updated_at
    await asyncio.sleep(0.01)
    await note.soft_delete()
    await note.refresh_from_db()
    assert note.updated_at > before


async def test_soft_delete_manager_hides_deleted_rows_by_default(db):
    shown = await HiddenNote.create(title="shown")
    hidden = await HiddenNote.create(title="hidden")
    await hidden.soft_delete()
    assert [n.id for n in await HiddenNote.all()] == [shown.id]
    assert await HiddenNote.filter(title="hidden").count() == 0
    assert await HiddenNote.get_or_none(id=hidden.id) is None
    assert [n.title for n in await HiddenNote.only_deleted()] == ["hidden"]
