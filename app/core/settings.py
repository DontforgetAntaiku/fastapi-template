import json
import logging
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_ignore_empty=True
    )


class DatabaseSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="DB_")

    USER: str
    PASSWORD: SecretStr | None = None
    HOST: str
    PORT: int = 5432
    NAME: str


class RedisSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    HOST: str
    PORT: int = 6379
    PASSWORD: SecretStr | None = None
    DB: int = 0


class AppSettings(_Base):
    model_config = SettingsConfigDict(env_prefix="CONF_")

    SESSION_SECRET: SecretStr
    LOGIN_SECRET: SecretStr
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SESSION_TTL: int = Field(default=86400, ge=60)
    ALLOW_REGISTRATION: bool = False
    TELEGRAM_BOT_TOKEN: SecretStr | None = None
    TELEGRAM_AUTH_MAX_AGE: int = Field(default=86400, ge=30)
    ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("LOG_LEVEL")
    @classmethod
    def _check_log_level(cls, value: str) -> str:
        value = value.upper()
        levels = [
            name for name in logging.getLevelNamesMapping() if isinstance(name, str)
        ]
        if value not in levels:
            raise ValueError(f"must be one of {sorted(levels)}")
        return value

    @field_validator("ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def log_level_no(self) -> int:
        return logging.getLevelNamesMapping()[self.LOG_LEVEL]


class Settings:
    def __init__(self) -> None:
        self.database = DatabaseSettings()  # pyright: ignore[reportCallIssue]
        self.redis = RedisSettings()  # pyright: ignore[reportCallIssue]
        self.app = AppSettings()  # pyright: ignore[reportCallIssue]


@lru_cache
def get_settings() -> Settings:
    return Settings()
