import datetime as dt
import decimal
import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, create_model
from tortoise.models import Model
from tortoise.queryset import QuerySet

_TEXT = {
    "exact", "iexact", "contains", "icontains", "startswith", "istartswith",
    "endswith", "iendswith", "in", "not", "not_in", "isnull",
}  # fmt: skip
_ORDERED = {"exact", "not", "in", "not_in", "gt", "gte", "lt", "lte", "isnull"}
_ORDERED_NO_IN = _ORDERED - {"in", "not_in"}
_EQUALITY = {"exact", "not", "in", "not_in", "isnull"}
_FLAG = {"exact", "not", "isnull"}

_TYPES: dict[type, tuple[set[str], tuple[str, ...]]] = {
    str: (_TEXT, ("exact", "icontains", "istartswith", "in")),
    int: (_ORDERED, ("exact", "in", "gt", "gte", "lt", "lte")),
    float: (_ORDERED_NO_IN, ("exact", "gt", "gte", "lt", "lte")),
    decimal.Decimal: (_ORDERED_NO_IN, ("exact", "gt", "gte", "lt", "lte")),
    dt.datetime: (_ORDERED_NO_IN, ("gt", "gte", "lt", "lte")),
    dt.date: (_ORDERED_NO_IN, ("gt", "gte", "lt", "lte")),
    uuid.UUID: (_EQUALITY, ("exact", "in")),
    bool: (_FLAG, ("exact",)),
}
_SORTABLE = (str, int, float, decimal.Decimal, dt.datetime, dt.date, uuid.UUID, bool)
_RESERVED = {"sort", "limit", "offset"}
_SENSITIVE = re.compile(r"password|secret|token|hash", re.IGNORECASE)
_MAX_IN_ITEMS = 100


class FilterSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: str
    limit: int
    offset: int

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    def lookups(self) -> dict[str, Any]:
        return self.model_dump(exclude=_RESERVED, exclude_none=True)

    def apply_filters(self, queryset: QuerySet) -> QuerySet:
        return queryset.filter(**self.lookups())

    def paginate(self, queryset: QuerySet) -> QuerySet:
        return queryset.order_by(self.sort).offset(self.offset).limit(self.limit)

    def apply(self, queryset: QuerySet) -> QuerySet:
        return self.paginate(self.apply_filters(queryset))


def _db_fields(model: type[Model]) -> dict[str, Any]:
    fields_map = model._meta.fields_map
    return {
        name: fields_map[name]
        for name in model._meta.fields_db_projection
        if name in fields_map and fields_map[name].field_type in _TYPES
    }


def _annotation(field: Any, lookup: str) -> Any:
    py_type = field.field_type
    if lookup == "isnull":
        return bool
    item: Any = py_type
    if py_type is str:
        max_length = getattr(field, "max_length", None) or 255
        item = Annotated[str, StringConstraints(max_length=max_length)]
    if lookup in ("in", "not_in"):
        return Annotated[list[item], Field(max_length=_MAX_IN_ITEMS)]
    return item


def filterset_for(
    model: type[Model],
    *,
    fields: Mapping[str, Sequence[str]] | None = None,
    sort: Sequence[str] | None = None,
    exclude: Sequence[str] = (),
    default_limit: int = 50,
    max_limit: int = 100,
    name: str | None = None,
) -> type[FilterSet]:
    available = _db_fields(model)
    private = set(getattr(model, "private_fields", ()))

    if fields is None:
        chosen: dict[str, Sequence[str]] = {}
        for column, field in available.items():
            if column in private or column in exclude or _SENSITIVE.search(column):
                continue
            lookups = list(_TYPES[field.field_type][1])
            if field.null:
                lookups.append("isnull")
            chosen[column] = lookups
    else:
        chosen = dict(fields)

    definitions: dict[str, Any] = {}
    for column, lookups in chosen.items():
        if column in _RESERVED:
            raise ValueError(
                f"{model.__name__}.{column}: name clashes with paging/sort"
            )
        if column not in available:
            raise ValueError(f"{model.__name__}.{column}: not a filterable column")
        if column in private:
            raise ValueError(f"{model.__name__}.{column}: private field")
        field = available[column]
        allowed = _TYPES[field.field_type][0]
        for lookup in lookups:
            if lookup not in allowed:
                raise ValueError(
                    f"{model.__name__}.{column}: lookup '{lookup}' is not valid for "
                    f"{field.field_type.__name__}"
                )
            key = column if lookup == "exact" else f"{column}__{lookup}"
            definitions[key] = (_annotation(field, lookup) | None, None)

    sortable = [
        column
        for column, field in available.items()
        if field.field_type in _SORTABLE and column not in private
    ]
    if sort is not None:
        unknown = set(sort) - set(available)
        if unknown:
            raise ValueError(f"{model.__name__}: cannot sort by {sorted(unknown)}")
        sortable = list(sort)
    pk = model._meta.pk_attr
    if pk not in sortable:
        sortable.insert(0, pk)
    sort_values = tuple(sortable) + tuple(f"-{column}" for column in sortable)

    return create_model(  # pyright: ignore[reportCallIssue]
        name or f"{model.__name__}Filter",
        __base__=FilterSet,
        sort=(Literal[sort_values], sort_values[0]),  # pyright: ignore[reportInvalidTypeArguments]
        limit=(int, Field(default=default_limit, ge=1, le=max_limit)),
        offset=(int, Field(default=0, ge=0, le=100_000)),
        **definitions,
    )
