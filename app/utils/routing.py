from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from fastapi.openapi.constants import METHODS_WITH_BODY
from fastapi.types import DecoratedCallable

METHODS_WITH_BODY.add("QUERY")  # in place: fastapi.openapi.utils shares this set object


class QueryRouter(APIRouter):
    def query(
        self, path: str, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.api_route(path, methods=["QUERY"], **kwargs)
