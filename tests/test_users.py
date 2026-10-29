from uuid import UUID, uuid4

from tests.conftest import login

BASE = "/api/v1/users"


async def _create(client, **overrides):
    payload = {"first_name": "Ada", "telegram_id": 1001, **overrides}
    return await client.post(BASE, json=payload)


async def test_create_and_get(admin_client):
    created = await _create(admin_client)
    assert created.status_code == 201
    body = created.json()
    assert UUID(body["id"]).version == 7
    assert body["telegram_id"] == 1001
    assert "password_hash" not in body

    fetched = await admin_client.get(f"{BASE}/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


async def test_private_fields_cannot_be_set_through_the_api(admin_client):
    response = await _create(admin_client, password_hash="x")
    assert response.status_code == 422
    assert (await _create(admin_client)).status_code == 201


async def test_list_with_query_parameters(admin_client):
    for i in range(3):
        await _create(admin_client, telegram_id=2000 + i, username=f"user{i}")
    response = await admin_client.get(BASE, params={"username__icontains": "user"})
    assert [u["username"] for u in response.json()] == ["user0", "user1", "user2"]

    page = await admin_client.get(BASE, params={"limit": 2, "sort": "-username"})
    assert [u["username"] for u in page.json()] == ["user2", "user1"]
    ids = await admin_client.get(
        BASE, params=[("telegram_id__in", 2000), ("telegram_id__in", 2002)]
    )
    assert len(ids.json()) == 2


async def test_unknown_query_parameter_is_rejected(admin_client):
    assert (
        await admin_client.get(BASE, params={"password_hash": "x"})
    ).status_code == 422
    assert (
        await admin_client.get(BASE, params={"sort": "password_hash"})
    ).status_code == 422


async def test_patch_updates_only_sent_fields(admin_client):
    user = (await _create(admin_client, last_name="Lovelace")).json()
    response = await admin_client.patch(
        f"{BASE}/{user['id']}", json={"first_name": "Augusta"}
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Augusta"
    assert response.json()["last_name"] == "Lovelace"
    assert response.json()["updated_at"] >= user["updated_at"]


async def test_delete(admin_client):
    user = (await _create(admin_client)).json()
    assert (await admin_client.delete(f"{BASE}/{user['id']}")).status_code == 204
    assert (await admin_client.get(f"{BASE}/{user['id']}")).status_code == 404


async def test_missing_user_is_404_with_request_id(admin_client):
    response = await admin_client.get(f"{BASE}/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["request_id"] == response.headers["x-request-id"]


async def test_duplicate_telegram_id_is_409(admin_client):
    await _create(admin_client)
    response = await _create(admin_client)
    assert response.status_code == 409
    assert response.json()["detail"] == "Conflict with existing data"


async def test_invalid_body_is_422(admin_client):
    assert (await admin_client.post(BASE, json={})).status_code == 422


async def test_anonymous_gets_401(client):
    assert (await client.get(BASE)).status_code == 401
    assert (await client.post(BASE, json={"first_name": "x"})).status_code == 401


async def test_regular_user_can_read_but_not_write(user_client):
    assert (await user_client.get(BASE)).status_code == 200
    assert (await _create(user_client)).status_code == 403
    assert (await user_client.delete(f"{BASE}/{uuid4()}")).status_code == 403


async def test_write_without_csrf_token_is_403(admin_client):
    del admin_client.headers["X-CSRF-Token"]
    response = await _create(admin_client)
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


async def test_write_from_foreign_origin_is_403(admin_client):
    response = await admin_client.post(
        BASE, json={"first_name": "x"}, headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403


async def test_write_from_allowed_origin_works(admin_client):
    response = await admin_client.post(
        BASE,
        json={"first_name": "x"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 201


async def _query(client, **body):
    return await client.request("QUERY", BASE, json=body)


async def test_query_filters_sorts_and_pages(admin_client):
    await _create(admin_client, telegram_id=1, username="alice")
    await _create(admin_client, telegram_id=2, username="alina")
    await _create(admin_client, telegram_id=3, username="bob")

    found = await _query(admin_client, username__icontains="ali", sort="-username")
    assert found.status_code == 200
    assert [u["telegram_id"] for u in found.json()] == [2, 1]
    assert [
        u["telegram_id"] for u in (await _query(admin_client, telegram_id=3)).json()
    ] == [3]
    assert len((await _query(admin_client, limit=1, offset=1)).json()) == 1
    assert len((await _query(admin_client)).json()) == 4


async def test_query_validates_body(admin_client):
    assert (await _query(admin_client, limit=0)).status_code == 422
    assert (await _query(admin_client, sort="password")).status_code == 422
    assert (await _query(admin_client, password_hash="x")).status_code == 422


async def test_query_needs_login_but_no_csrf_token(user_client):
    del user_client.headers["X-CSRF-Token"]
    assert (await _query(user_client)).status_code == 200


async def test_query_preflight_is_allowed(client):
    response = await client.options(
        BASE,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "QUERY",
            "Access-Control-Request-Headers": "x-csrf-token,content-type",
        },
    )
    assert response.status_code == 200
    assert "QUERY" in response.headers["access-control-allow-methods"]
    assert "x-csrf-token" in response.headers["access-control-allow-headers"].lower()


async def test_login_helper_is_reusable(client, make_user):
    await make_user("grace")
    assert await login(client, "grace")
