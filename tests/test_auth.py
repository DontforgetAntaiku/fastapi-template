import time

from app.database.models import User
from app.utils.auth import hash_password, verify_password
from tests.conftest import PASSWORD, login
from tests.helpers import sign_init_data, sign_widget

AUTH = "/api/v1/auth"


async def test_login_me_logout(client, make_user):
    user = await make_user("ada")
    response = await client.post(
        f"{AUTH}/login", json={"username": "ada", "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == str(user.id)
    assert "password_hash" not in body["user"]
    csrf = body["csrf_token"]

    me = await client.get(f"{AUTH}/me")
    assert me.status_code == 200
    assert me.json()["csrf_token"] == csrf

    client.headers["X-CSRF-Token"] = csrf
    assert (await client.post(f"{AUTH}/logout")).status_code == 204
    assert (await client.get(f"{AUTH}/me")).status_code == 401


async def test_logout_really_revokes_the_session(client, make_user, redis):
    await make_user("ada")
    await login(client)
    assert await redis.keys("sess:*")
    stolen_cookie = client.cookies.get("session")
    await client.post(f"{AUTH}/logout")
    assert not await redis.keys("sess:*")

    client.cookies.set("session", stolen_cookie)
    assert (await client.get(f"{AUTH}/me")).status_code == 401


async def test_wrong_password_and_unknown_user_look_the_same(client, make_user):
    await make_user("ada")
    wrong = await client.post(
        f"{AUTH}/login", json={"username": "ada", "password": "nope"}
    )
    unknown = await client.post(
        f"{AUTH}/login", json={"username": "ghost", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Invalid credentials"


async def test_inactive_user_cannot_log_in(client, make_user):
    await make_user("ada", is_active=False)
    response = await client.post(
        f"{AUTH}/login", json={"username": "ada", "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_login_is_throttled_after_five_failures(client, make_user):
    await make_user("ada")
    for _ in range(5):
        bad = await client.post(
            f"{AUTH}/login", json={"username": "ada", "password": "x"}
        )
        assert bad.status_code == 401
    blocked = await client.post(
        f"{AUTH}/login", json={"username": "ada", "password": PASSWORD}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


async def test_success_resets_the_username_counter(client, make_user, redis):
    await make_user("ada")
    for _ in range(3):
        await client.post(f"{AUTH}/login", json={"username": "ada", "password": "x"})
    await login(client)
    assert len(await redis.keys("thr:login:*")) == 1


async def test_login_from_foreign_origin_is_403(client, make_user):
    await make_user("ada")
    response = await client.post(
        f"{AUTH}/login",
        json={"username": "ada", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


async def test_new_session_id_on_every_login(client, make_user, redis):
    await make_user("ada")
    await login(client)
    first = (await redis.keys("sess:*"))[0]
    await login(client)
    keys = await redis.keys("sess:*")
    assert len(keys) == 1 and keys[0] != first


async def test_disabled_user_loses_the_session(client, make_user):
    user = await make_user("ada")
    await login(client)
    user.is_active = False
    await user.save()
    assert (await client.get(f"{AUTH}/me")).status_code == 401


async def test_long_password_is_a_clean_422(client):
    response = await client.post(
        f"{AUTH}/login", json={"username": "ada", "password": "a" * 5000}
    )
    assert response.status_code == 422


async def test_password_helpers_rehash_and_dummy_compare():
    stored = await hash_password("secret-password")
    assert (await verify_password(stored, "secret-password"))[0] is True
    assert (await verify_password(stored, "other"))[0] is False
    assert (await verify_password(None, "anything"))[0] is False


async def test_register_creates_a_user_who_can_log_in(client):
    response = await client.post(
        f"{AUTH}/register",
        json={"username": "newbie", "password": "long-enough-pw", "first_name": "New"},
    )
    assert response.status_code == 201
    assert response.json()["is_admin"] is False
    assert await login(client, "newbie", "long-enough-pw")


async def test_register_rejects_weak_input_and_duplicates(client, make_user):
    await make_user("taken")
    body = {"username": "taken", "password": "long-enough-pw", "first_name": "X"}
    assert (await client.post(f"{AUTH}/register", json=body)).status_code == 409
    short = {**body, "username": "fresh", "password": "short"}
    assert (await client.post(f"{AUTH}/register", json=short)).status_code == 422
    odd = {**body, "username": "bad name!"}
    assert (await client.post(f"{AUTH}/register", json=odd)).status_code == 422


async def test_register_is_rate_limited(client):
    for i in range(5):
        r = await client.post(
            f"{AUTH}/register",
            json={
                "username": f"user{i}",
                "password": "long-enough-pw",
                "first_name": "U",
            },
        )
        assert r.status_code == 201
    r = await client.post(
        f"{AUTH}/register",
        json={"username": "user9", "password": "long-enough-pw", "first_name": "U"},
    )
    assert r.status_code == 429


def _paths(settings_patch: dict) -> set[str]:
    from fastapi import FastAPI

    from app.core.settings import Settings
    from app.routers.v1 import build_router

    settings = Settings()
    settings.app = settings.app.model_copy(update=settings_patch)
    app = FastAPI()
    app.include_router(build_router(settings))
    return set(app.openapi()["paths"])


def test_optional_routes_are_not_mounted_when_disabled():
    off = _paths({"ALLOW_REGISTRATION": False, "TELEGRAM_BOT_TOKEN": None})
    assert "/v1/auth/login" in off
    assert "/v1/auth/register" not in off
    assert not any("telegram" in path for path in off)
    on = _paths({})
    assert "/v1/auth/register" in on and "/v1/auth/telegram/webapp" in on


TG_USER = {"id": 777, "first_name": "Tele", "last_name": "Gram", "username": "tele"}


async def test_telegram_webapp_login_creates_a_user_and_a_session(client):
    response = await client.post(
        f"{AUTH}/telegram/webapp", json={"init_data": sign_init_data(TG_USER)}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["telegram_id"] == 777
    assert body["user"]["is_admin"] is False
    assert (await client.get(f"{AUTH}/me")).status_code == 200
    again = await client.post(
        f"{AUTH}/telegram/webapp", json={"init_data": sign_init_data(TG_USER)}
    )
    assert again.json()["user"]["id"] == body["user"]["id"]
    assert await User.filter(telegram_id=777).count() == 1


async def test_telegram_webapp_rejects_forgery_and_old_data(client):
    good = sign_init_data(TG_USER)
    tampered = good.replace("Tele", "Evil")
    wrong_bot = sign_init_data(TG_USER, token="999:OTHER")
    old = sign_init_data(TG_USER, auth_date=int(time.time()) - 10 * 86400)
    for bad in (tampered, wrong_bot, old, "garbage"):
        r = await client.post(f"{AUTH}/telegram/webapp", json={"init_data": bad})
        assert r.status_code == 401, bad
    assert await User.filter(telegram_id=777).count() == 0


async def test_telegram_widget_login(client):
    data = sign_widget(
        {
            "id": 888,
            "first_name": "Wid",
            "username": "wid",
            "auth_date": int(time.time()),
        }
    )
    response = await client.post(f"{AUTH}/telegram/widget", json=data)
    assert response.status_code == 200
    assert response.json()["user"]["telegram_id"] == 888

    forged = {**data, "id": 889}
    assert (
        await client.post(f"{AUTH}/telegram/widget", json=forged)
    ).status_code == 401


async def test_telegram_user_cannot_log_in_with_a_password(client):
    await client.post(
        f"{AUTH}/telegram/webapp", json={"init_data": sign_init_data(TG_USER)}
    )
    user = await User.get(telegram_id=777)
    assert user.password_hash is None and user.username is None


async def test_disabled_telegram_account_is_refused(client):
    await User.create(telegram_id=777, first_name="Tele", is_active=False)
    response = await client.post(
        f"{AUTH}/telegram/webapp", json={"init_data": sign_init_data(TG_USER)}
    )
    assert response.status_code == 403


async def test_create_admin_command_is_idempotent(db):
    from app.cli import create_admin

    first = await create_admin("root", "first-password")
    second = await create_admin("root", "second-password")
    assert first.id == second.id
    assert (await verify_password(second.password_hash, "second-password"))[0]
    assert second.is_admin
