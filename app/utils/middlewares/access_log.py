import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_id import get_request_id

logger = logging.getLogger("app.access")


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status = 500

        async def send_and_capture(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        finally:
            path = scope["path"]
            level = logging.DEBUG if path.endswith("/health") else logging.INFO
            logger.log(
                level,
                "%s %s -> %d %.1fms request_id=%s",
                scope["method"],
                path,
                status,
                (time.perf_counter() - started) * 1000,
                get_request_id(scope),
            )
