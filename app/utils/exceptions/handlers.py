from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from tortoise.exceptions import DoesNotExist, IntegrityError

from app.utils.middlewares.request_id import REQUEST_ID_HEADER, get_request_id


def _error(
    request: Request,
    status_code: int,
    detail: Any,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request.scope)
    headers = dict(extra_headers or {})
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        {"detail": detail, "request_id": request_id},
        status_code=status_code,
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast(StarletteHTTPException, exc)
    return _error(request, exc.status_code, exc.detail, dict(exc.headers or {}))


async def does_not_exist_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(request, 404, "Not found")


async def integrity_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(request, 409, "Conflict with existing data")


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(request, 500, "Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(DoesNotExist, does_not_exist_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
