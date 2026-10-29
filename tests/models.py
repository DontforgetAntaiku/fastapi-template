from tortoise import fields

from app.database.base import AppModel
from app.utils.classes.mixin import SoftDeleteManager, SoftDeleteMixin


class Note(AppModel, SoftDeleteMixin):
    title = fields.CharField(max_length=100)

    class Meta:  # pyright: ignore
        table = "test_notes"


class HiddenNote(AppModel, SoftDeleteMixin):
    title = fields.CharField(max_length=100)
    secret_code = fields.CharField(max_length=20, default="x")

    class Meta:  # pyright: ignore
        table = "test_hidden_notes"
        manager = SoftDeleteManager()
