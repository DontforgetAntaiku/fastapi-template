from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import betterlogging as bl
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import RegisterTortoise

from app.core import CONFIG, LOG_LEVEL, TEMPLATES
from app.database import TORTOISE_ORM
from app.routers import routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with RegisterTortoise(config=TORTOISE_ORM)(app):
        yield


def main():
    bl.basic_colorized_config(level=LOG_LEVEL)

    app = FastAPI(
        debug=True,
        lifespan=lifespan,
        # docs_url=None,
        redoc_url=None,
    )
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.add_middleware(
        SessionMiddleware,
        secret_key=CONFIG.configuration.SESSION_SECRET,
        session_cookie="session",
        max_age=3600,
        same_site="lax",
    )
    for router in routers:
        app.include_router(router=router)

    return app


app = main()


@app.exception_handler(Exception)
async def http_exception_handler(request: Request, exc: Exception):
    if request.headers.get("hx-request"):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    return TEMPLATES.TemplateResponse(
        "generic_error.html",
        {
            "request": request,
            "status_code": 500,
            "error_title": "Произошла ошибка",
            "error_message": "При обработке вашего запроса произошла непредвиденная ошибка.",
            "detail": str(exc),
        },
        status_code=500,
    )
