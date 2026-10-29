# FastAPI template

FastAPI + Tortoise ORM (PostgreSQL) + Redis backend template.
Python 3.14, managed with [uv](https://docs.astral.sh/uv/).

Included: typed settings, sessions with CSRF protection, optional Telegram login, rate
limiting, readiness probe, UUIDv7 base models, generated schemas and filters, the HTTP
`QUERY` method with typed TypeScript clients, request ids, one error format, tests, Docker.

## Quick start

```bash
cp .env.example .env        # fill in the values, set CONF_DEBUG=true for local work
uv sync                     # installs runtime + dev dependencies
uv run tortoise migrate     # applies app/database/migrations
ADMIN_PASSWORD=... uv run python -m app.cli create-admin admin   # first admin
uv run python main.py       # http://localhost:8000, docs at /api/docs (debug only)
```

## Configuration

Settings are typed [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
classes in [app/core/settings.py](app/core/settings.py), read from environment variables
(`.env` is loaded if present; real environment variables win; empty values count as unset).
Get them with `get_settings()` (cached, nothing is read at import time); secrets are
`SecretStr`, so they never show up in logs or `repr`.

| Variable | Notes |
|---|---|
| `DB_USER` `DB_PASSWORD` `DB_HOST` `DB_PORT` `DB_NAME` | PostgreSQL connection |
| `REDIS_HOST` `REDIS_PORT` `REDIS_PASSWORD` `REDIS_DB` | Redis connection (`REDIS_DB` defaults to 0) |
| `CONF_SESSION_SECRET` | signs the session cookie |
| `CONF_LOGIN_SECRET` | keyed hash of client IPs / usernames in rate-limit keys |
| `CONF_DEBUG` | `true` only in development: debug tracebacks, `/api/docs`, non-`Secure` cookie, auto-creates a missing database. Default `false`. |
| `CONF_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR`, default `INFO` |
| `CONF_ORIGINS` | CORS origins: `http://a,http://b` or a JSON list |
| `CONF_SESSION_TTL` | session lifetime in seconds (default 86400) |
| `CONF_ALLOW_REGISTRATION` | mounts `POST /api/v1/auth/register` (default `false`) |
| `CONF_TELEGRAM_BOT_TOKEN` | set it to mount Telegram login; unset = no Telegram routes |
| `CONF_TELEGRAM_AUTH_MAX_AGE` | how old Telegram login data may be, seconds (default 86400) |

A missing or invalid variable stops the app at start and the error names it.

## Layout

```
main.py                     create_app(): middlewares, handlers, routers, lifespan
app/cli.py                  python -m app.cli create-admin <username>
app/core/                   settings.py, redis.py, dependencies.py (RedisDep, SettingsDep)
app/database/               base.py (AppModel), models.py, filters/, migrations/
app/routers/main/           unversioned routes: /api/health, /api/ready
app/routers/v1/             versioned API (/api/v1/...), one folder per resource
app/utils/classes/          mixin.py: PydanticMixin, SoftDeleteMixin, SoftDeleteManager
app/utils/dataclasses/      TelegramUser
app/utils/schemas/          request/response models (user, auth)
app/utils/services/         auth.py: login, registration and Telegram flows
app/utils/exceptions/       TelegramAuthError, global exception handlers
app/utils/middlewares/      request id, access log
app/utils/auth.py           sessions, CSRF, Origin check, argon2, require_user/require_admin
app/utils/ratelimit.py      rate_limit dependency, FailureThrottle
app/utils/telegram.py       Telegram login verification
app/utils/routing.py        QueryRouter (HTTP QUERY)
app/utils/openapi.py        spec conversion for TypeScript generators
scripts/export_openapi.py   writes the OpenAPI document (no server needed)
client/query-method.ts      openapi-fetch middleware, copy into the frontend
tests/                      pytest (in-memory SQLite + fake Redis, no services needed)
```

Every route lives under `/api`. Business routes are versioned (`/api/v1/users`);
probes are not, because they should not change with the API version.

## Authentication

Cookie sessions, not tokens in JavaScript. The signed `session` cookie holds only an opaque
`sid`; the real session lives in Redis (`sess:<sid>`, TTL = `CONF_SESSION_TTL`), so logout
revokes it, and a new `sid` is issued at every login.

| Endpoint | |
|---|---|
| `POST /api/v1/auth/login` `{username, password}` | returns `{user, csrf_token}` |
| `GET /api/v1/auth/me` | same payload (use it after a page reload) |
| `POST /api/v1/auth/logout` | 204, destroys the session |
| `POST /api/v1/auth/register` | only with `CONF_ALLOW_REGISTRATION=true` |
| `POST /api/v1/auth/telegram/webapp` `{init_data}` | only with `CONF_TELEGRAM_BOT_TOKEN` (Mini Apps) |
| `POST /api/v1/auth/telegram/widget` widget fields | only with `CONF_TELEGRAM_BOT_TOKEN` (Login Widget) |

* **CSRF:** every unsafe request (anything except GET/HEAD/OPTIONS/QUERY) must send the token
  in `X-CSRF-Token`. Keep it in memory, not in localStorage. Browsers send `credentials: "include"`.
* **Origin:** an unsafe request with an `Origin` header must come from `CONF_ORIGINS` or the
  API's own host.
* **Passwords:** argon2id, hashed in a thread; unknown users are checked against a dummy hash
  so response time does not reveal accounts.
* **Brute force:** 5 failed logins per client and per username within 15 minutes give 429
  with `Retry-After`. A successful login resets only the username counter.
* **Telegram:** `app/utils/telegram.py` verifies the HMAC of `initData` / widget data and its
  age; accounts are matched by `telegram_id` and created on first login (no password, no
  `username`, never admin).
* **Code layout:** route files only declare routes; the flows live in
  `app/utils/services/auth.py` and the request/response models in `app/utils/schemas/`.
* **Protecting routes:** `user: CurrentUser` or `AdminUser` as a parameter, or
  `dependencies=[Depends(require_admin)]` (see `app/routers/v1/users/view.py`). Reads need a
  login, writes need an admin.

Create the first admin with `python -m app.cli create-admin <username>` (password from
`ADMIN_PASSWORD` or a prompt; safe to re-run to reset a password).

## Rate limiting

```python
@router.post("", dependencies=[Depends(rate_limit("5/hour"))])      # "N/unit", "10/15min"
```

Counted per client and route in Redis; over the limit gives 429 and `Retry-After`. Clients
are identified by an HMAC of their IP (`CONF_LOGIN_SECRET`), never the raw address. Behind a
reverse proxy start uvicorn with `FORWARDED_ALLOW_IPS=<proxy ip>` so the real client address
is used; do not parse `X-Forwarded-For` yourself. `FailureThrottle` (in the same module)
counts only failures, as the login does.

## Health and readiness

* `GET /api/health` is liveness and touches nothing (use it as the container healthcheck).
* `GET /api/ready` checks the database and Redis (2 s each) and answers 200 or 503 with the
  status per dependency; use it for load balancers and deploy scripts.

## Models, serialization and filters

```python
class Product(AppModel):  # UUIDv7 id, created_at, updated_at
    title = fields.CharField(max_length=255)
    cost_price = fields.DecimalField(max_digits=10, decimal_places=2)
    private_fields = ("cost_price",)  # never in a schema or a filter


Product.get_pydantic_model()  # output schema  (response_model=...)
Product.get_input_model()  # request body   (no id / timestamps)
Product.get_update_model()  # PATCH body     (every field optional)
await product.to_pydantic()  # also .to_dict() / .to_json()
```

Models with relations need `Tortoise.init_models(...)` before the first schema call.

**Soft delete** (optional): `class Post(AppModel, SoftDeleteMixin)` adds `deleted_at`,
`await post.soft_delete()`, `restore()`, `Post.alive()` and `Post.only_deleted()`. To hide
deleted rows from every query add `class Meta: manager = SoftDeleteManager()`.

**Filters** are pydantic models generated from the model (`app/database/filters/`). Their
fields are Tortoise lookups (`username__icontains`, `created_at__gte`, `id__in`) plus `sort`,
`limit`, `offset`. Clients can only use what you allow, with bounded sizes.

```python
Filter = User.get_filter_model()                      # automatic: every column, sensible lookups
UserFilter = filterset_for(User, fields={"username": ["exact", "icontains"],
                                         "created_at": ["gte", "lte"]},
                           sort=["created_at", "username"])    # explicit: app/database/filters/users.py

@router.get("")   async def list_(filters: Annotated[UserFilter, Query()]): ...   # ?username__icontains=ad
@router.query("") async def search(filters: UserFilter): ...                       # JSON body
users = await filters.apply(User.all())          # or .apply_filters(qs).count(), .paginate(qs)
```

Automatic mode skips `private_fields` and columns whose name looks sensitive
(`password`, `secret`, `token`, `hash`). Unknown lookups fail when the app starts.

Add a resource: model, `uv run tortoise makemigrations`, a filter set, and
`app/routers/v1/<name>/view.py` (copy `users`) included in `app/routers/v1/__init__.py`.

## QUERY method and typed clients

`QueryRouter` ([app/utils/routing.py](app/utils/routing.py)) adds `@router.query(path)` for the
HTTP QUERY method: a safe, idempotent request with a JSON body (searches whose filters do not
fit a URL). The OpenAPI document is 3.2.0, the first version with a `query` operation. No
CSRF token is needed (it is a safe method); `QUERY` is in the CORS `allow_methods`.

`openapi-typescript` 7.13 ignores `query` operations, so generate the client types from a
converted spec in which each one is a POST on `<path>::QUERY`, and let a small middleware send
it as a real QUERY request:

```bash
uv run python scripts/export_openapi.py --typescript -o ../frontend/openapi.json
cd ../frontend && npm i openapi-fetch && npm i -D openapi-typescript typescript@5
npx openapi-typescript openapi.json -o src/api/schema.d.ts --default-non-nullable false
cp ../backend/client/query-method.ts src/api/       # then: api.use(queryMethod)
```

```ts
const { data } = await api.POST("/api/v1/users::QUERY", { body: { username__icontains: "ad" } });
```

Needs `typescript@5` (openapi-typescript 7 breaks on 6+) and `--default-non-nullable false`
(otherwise fields with defaults become required in request bodies). Operation ids are
`<tag>_<function>` (`users_search_users`). Unknown keys in a body are not a compile error
(a TypeScript limitation); wrong values are. Proxies and WAFs in front of the API must allow the method.

## Errors and logging

* Every response carries `X-Request-ID` (an incoming valid one is reused).
* Errors use one shape: `{"detail": "...", "request_id": "..."}`. `DoesNotExist` maps to
  404, `IntegrityError` to 409 (without SQL details), anything unhandled to 500.
* One access-log line per request with status, duration and request id.

## Redis

The client is created in the lifespan, stored in `app.state.redis` (strings in, strings out)
and closed on shutdown. Use it with `redis: Annotated[Redis, Depends(get_redis)]`
(`from app.core.redis import get_redis`). Override settings or dependencies in tests with
`app.dependency_overrides[...]`.

## Migrations

```bash
uv run tortoise makemigrations   # after changing models
uv run tortoise migrate
```

Keep migrations additive (new nullable columns/tables) so the previous release keeps
working on the new schema, and run them once per deploy, not on container start.

## Development

```bash
uv run python -m pytest          # SQLite in memory + fake Redis
uv run ruff check . && uv run ruff format .
uv run pyright
uv run pre-commit install        # hooks: ruff, pyright, uv-lock, pytest on push
```

## Docker

```bash
docker build -t fastapi-template .
docker run --rm --env-file .env -p 8000:8000 fastapi-template
docker run --rm --env-file .env fastapi-template tortoise migrate           # migrations
docker run --rm -it --env-file .env fastapi-template python -m app.cli create-admin admin
```

The image is multi-stage, runs as a non-root user and has a healthcheck on `/api/health`.
Production must run with `CONF_DEBUG=false` behind a TLS-terminating proxy (the session
cookie is `Secure`).
