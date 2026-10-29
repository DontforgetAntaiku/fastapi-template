from fastapi import APIRouter

from app.core.settings import Settings

from .main.view import router as main
from .v1 import build_router as build_v1


def get_routers(settings: Settings) -> tuple[APIRouter, ...]:
    return (main, build_v1(settings))


__all__ = ["get_routers"]
