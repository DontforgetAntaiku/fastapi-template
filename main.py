from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import betterlogging as bl
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from tortoise.contrib.fastapi import RegisterTortoise

from app.core import CONFIG, LOG_LEVEL
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
    app.add_middleware(
        SessionMiddleware,
        secret_key=CONFIG.configuration.SESSION_SECRET,
        session_cookie="session",
        max_age=3600,
        same_site="lax",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CONFIG.configuration.ORIGINGS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in routers:
        app.include_router(router=router, prefix="/api")

    return app


app = main()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0")
