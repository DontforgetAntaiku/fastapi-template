import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.utils.ratelimit import FailureThrottle, parse_rate, rate_limit


@pytest.mark.parametrize(
    ("spec", "expected"),
    [("5/minute", (5, 60)), ("100/hour", (100, 3600)), ("10/15min", (10, 900)),
     ("1/second", (1, 1)), ("3/days", (3, 86400))],
)  # fmt: skip
def test_parse_rate(spec, expected):
    assert parse_rate(spec) == expected


@pytest.mark.parametrize(
    "spec", ["", "5", "five/minute", "5/fortnight", "5 per minute"]
)
def test_parse_rate_rejects_garbage(spec):
    with pytest.raises(ValueError, match="bad rate limit"):
        parse_rate(spec)


@pytest.fixture
async def limited_client(db, redis):
    app = FastAPI()
    app.state.redis = redis

    @app.get("/a", dependencies=[Depends(rate_limit("2/minute"))])
    async def a():
        return "a"

    @app.get("/b", dependencies=[Depends(rate_limit("2/minute"))])
    async def b():
        return "b"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_limit_is_enforced_per_route(limited_client):
    assert [(await limited_client.get("/a")).status_code for _ in range(2)] == [
        200,
        200,
    ]
    blocked = await limited_client.get("/a")
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["retry-after"]) <= 60
    assert (await limited_client.get("/b")).status_code == 200


async def test_counter_expires(limited_client, redis):
    for _ in range(3):
        await limited_client.get("/a")
    (key,) = await redis.keys("rl:/a:*")
    assert 0 < await redis.ttl(key) <= 60
    await redis.delete(key)
    assert (await limited_client.get("/a")).status_code == 200


async def test_no_raw_ip_is_stored(limited_client, redis):
    await limited_client.get("/a")
    (key,) = await redis.keys("rl:*")
    assert "127.0.0.1" not in key


async def test_failure_throttle(redis):
    throttle = FailureThrottle("t", "2/minute")
    await throttle.check(redis, "who")
    await throttle.fail(redis, "who")
    await throttle.fail(redis, "who")
    with pytest.raises(Exception, match="429"):
        await throttle.check(redis, "who")
    await throttle.check(redis, "someone-else")
    await throttle.clear(redis, "who")
    await throttle.check(redis, "who")
