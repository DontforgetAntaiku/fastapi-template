import os

# set before the app is imported: settings read the environment on first use
for key, value in {
    "DB_USER": "test",
    "DB_PASSWORD": "test",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "test",
    "CONF_SESSION_SECRET": "test-session-secret",
    "CONF_LOGIN_SECRET": "test-login-secret",
    "CONF_DEBUG": "false",
    "CONF_ORIGINS": "http://localhost:5173",
    "CONF_ALLOW_REGISTRATION": "true",
    "CONF_TELEGRAM_BOT_TOKEN": "123456:TEST-TOKEN",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
}.items():
    os.environ[key] = value

import pytest_asyncio  # noqa: E402
from fakeredis import FakeAsyncRedis, FakeServer  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from tortoise import Tortoise  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest_asyncio.fixture
async def db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.database.models", "tests.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def redis():
    client = FakeAsyncRedis(server=FakeServer(), decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def client(db, redis):
    from main import app

    app.state.redis = redis
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield client


@pytest_asyncio.fixture
async def make_user(db):
    from app.database.models import User
    from app.utils.auth import hash_password

    async def _make(username="ada", password=PASSWORD, *, admin=False, **extra):
        extra.setdefault("first_name", username.title())
        return await User.create(
            username=username,
            password_hash=await hash_password(password),
            is_admin=admin,
            **extra,
        )

    return _make


async def login(client, username="ada", password=PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    csrf = response.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return csrf


@pytest_asyncio.fixture
async def admin_client(client, make_user):
    await make_user("admin", admin=True)
    await login(client, "admin")
    return client


@pytest_asyncio.fixture
async def user_client(client, make_user):
    await make_user("ada")
    await login(client, "ada")
    return client
