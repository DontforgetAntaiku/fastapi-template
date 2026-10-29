async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_when_dependencies_answer(client):
    response = await client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "redis": "ok"},
    }


async def test_ready_is_503_when_redis_is_down(client, redis, monkeypatch):
    async def broken_ping(*args, **kwargs):
        raise ConnectionError("redis is down")

    monkeypatch.setattr(redis, "ping", broken_ping)
    response = await client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "error"}
    assert "redis is down" not in response.text


async def test_request_id_is_generated(client):
    response = await client.get("/api/health")
    assert response.headers["x-request-id"]


async def test_request_id_is_echoed(client):
    response = await client.get("/api/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


async def test_invalid_request_id_is_replaced(client):
    response = await client.get("/api/health", headers={"X-Request-ID": "bad id!"})
    assert response.headers["x-request-id"] != "bad id!"
