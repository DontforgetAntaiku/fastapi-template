import pytest
from pydantic import ValidationError

from app.core.settings import AppSettings, DatabaseSettings, RedisSettings


def test_required_values_and_defaults(monkeypatch):
    monkeypatch.setenv("DB_USER", "u")
    monkeypatch.setenv("DB_HOST", "h")
    monkeypatch.setenv("DB_NAME", "n")
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    db = DatabaseSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert (db.USER, db.PORT, db.PASSWORD) == ("u", 5432, None)


def test_missing_required_lists_the_variable(monkeypatch):
    monkeypatch.delenv("DB_USER", raising=False)
    with pytest.raises(ValidationError, match="USER"):
        DatabaseSettings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_empty_values_count_as_unset(monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "r")
    monkeypatch.setenv("REDIS_DB", "")
    monkeypatch.setenv("REDIS_PASSWORD", "")
    redis = RedisSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert (redis.DB, redis.PASSWORD) == (0, None)


@pytest.mark.parametrize(
    "raw", ["http://a, http://b", '["http://a", "http://b"]', "http://a,http://b,"]
)
def test_origins_comma_or_json(monkeypatch, raw):
    monkeypatch.setenv("CONF_SESSION_SECRET", "s")
    monkeypatch.setenv("CONF_LOGIN_SECRET", "l")
    monkeypatch.setenv("CONF_ORIGINS", raw)
    conf = AppSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert conf.ORIGINS == ["http://a", "http://b"]


def test_log_level_validated_and_secrets_hidden(monkeypatch):
    monkeypatch.setenv("CONF_SESSION_SECRET", "topsecret")
    monkeypatch.setenv("CONF_LOGIN_SECRET", "l")
    monkeypatch.setenv("CONF_LOG_LEVEL", "debug")
    conf = AppSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert conf.log_level_no == 10
    assert "topsecret" not in repr(conf)

    monkeypatch.setenv("CONF_LOG_LEVEL", "loud")
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        AppSettings(_env_file=None)  # pyright: ignore[reportCallIssue]
