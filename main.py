from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import betterlogging as bl
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import RegisterTortoise

from app.core import get_settings
from app.core.redis import create_redis
from app.database import build_tortoise_config
from app.routers import get_routers
from app.utils.exceptions.handlers import register_exception_handlers
from app.utils.middlewares.access_log import AccessLogMiddleware
from app.utils.middlewares.request_id import REQUEST_ID_HEADER, RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.redis = create_redis(settings)
    try:
        async with RegisterTortoise(config=build_tortoise_config(settings))(app):
            yield
    finally:
        await app.state.redis.aclose()


def _operation_id(route: APIRoute) -> str:
    return f"{route.tags[0]}_{route.name}" if route.tags else route.name


def create_app() -> FastAPI:
    settings = get_settings()
    debug = settings.app.DEBUG
    bl.basic_colorized_config(level=settings.app.log_level_no)

    app = FastAPI(
        debug=debug,
        lifespan=lifespan,
        docs_url="/api/docs" if debug else None,
        openapi_url="/api/openapi.json" if debug else None,
        redoc_url=None,
        generate_unique_id_function=_operation_id,
    )
    app.openapi_version = "3.2.0"
    register_exception_handlers(app)

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app.SESSION_SECRET.get_secret_value(),
        session_cookie="session",
        max_age=settings.app.SESSION_TTL,
        same_site="lax",
        https_only=not debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "QUERY", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    for router in get_routers(settings):
        app.include_router(router=router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8000)
