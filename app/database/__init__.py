from app.core import CONFIG

user, password, host, port, dbname = (
    CONFIG.database.USER,
    CONFIG.database.PASSWORD,
    CONFIG.database.HOST,
    CONFIG.database.PORT,
    CONFIG.database.NAME,
)


TORTOISE_ORM = {
    "connections": {"default": f"postgres://{user}:{password}@{host}:{port}/{dbname}"},
    "apps": {
        "models": {
            "models": [
                "app.database.models",
            ],
            "default_connection": "default",
            "migrations": "models.migrations",
        },
    },
    "use_tz": True,
    "_create_db": True,
}


__all__ = ("TORTOISE_ORM",)
