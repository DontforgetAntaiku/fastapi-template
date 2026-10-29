from typing import Any

from app.core import Settings, get_settings


def build_tortoise_config(settings: Settings) -> dict[str, Any]:
    password = settings.database.PASSWORD
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": settings.database.HOST,
                    "port": settings.database.PORT,
                    "user": settings.database.USER,
                    "password": password.get_secret_value() if password else None,
                    "database": settings.database.NAME,
                },
            },
        },
        "apps": {
            "models": {
                "models": ["app.database.models"],
                "default_connection": "default",
                "migrations": "app.database.migrations",
            },
        },
        "use_tz": True,
        "_create_db": settings.app.DEBUG,
    }


TORTOISE_ORM = build_tortoise_config(get_settings())

__all__ = ("TORTOISE_ORM", "build_tortoise_config")
