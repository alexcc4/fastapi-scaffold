# FastAPI Scaffold

A minimal template for internal FastAPI services with asynchronous MySQL,
Redis, Alembic, internal account authentication, request observability, and
Pytest.

## Requirements

- Python >= 3.12
- MySQL 8.x
- Redis
- [uv](https://docs.astral.sh/uv/)

## Create a Project

After creating a repository from this template, update the project name in
`pyproject.toml`, the FastAPI title, and the example database names.

```bash
uv sync --group dev
cp .env.example .env.development
```

Update `.env.development` for your local environment, then create the
development database:

```bash
mysql -u root -p -e \
  "CREATE DATABASE IF NOT EXISTS fastapi_scaffold CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## Start the Application

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --no-access-log
```

After startup, the following endpoints are available:

- Liveness probe: `http://localhost:8000/ping`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

`/ping` indicates only that the application can respond. It does not check
MySQL or Redis.

Application middleware adds `X-Request-ID` and `Server-Timing` to HTTP
responses and writes one access log entry without the query string, request
body, or authentication information. Disable Uvicorn's access log to avoid
duplicate entries.

## Internal Accounts

Create the first internal account:

```bash
uv run python -m app.cli create-user scaffold.admin --name "Scaffold Admin"
```

The password is entered through a hidden interactive prompt. Account
maintenance commands:

```bash
uv run python -m app.cli reset-password scaffold.admin
uv run python -m app.cli disable-user scaffold.admin
uv run python -m app.cli enable-user scaffold.admin
uv run python -m app.cli inspect-session
```

`inspect-session` also reads the token from a hidden prompt and prints only its
digest fingerprint, user ID, versions, and remaining TTL. Redis keys use the
token's SHA-256 digest; the raw token is never stored or printed.

The login endpoint is `POST /api/auth/token` and uses an OAuth2 password form.
Subsequent requests use `Authorization: Bearer <token>` to access
`/api/auth/me` and `/api/auth/logout`.

## Testing

Tests connect to real MySQL and Redis instances by default:

```bash
cp .env.test.example .env.test
mysql -u root -p -e \
  "CREATE DATABASE IF NOT EXISTS test_fastapi_scaffold CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
uv run pytest
```

The test database name must start with `test_`. Redis must use a disposable,
nonzero database; tests run `FLUSHDB` before and after every Redis test. The
complete suite uses Alembic to downgrade the test database to base and then
upgrade it to head, so the database must be dedicated and safe to clear.

For fast feedback without infrastructure-dependent tests:

```bash
uv run pytest -m "not integration"
```

Application configuration is still loaded during test collection, so fast
tests also require a parseable `.env.test`. They do not connect to the
configured MySQL or Redis instances.

## Database Migrations

After adding a model, import it in `app/models/__init__.py` before generating a
migration:

```bash
uv run alembic revision --autogenerate -m "describe change in English"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Slow Queries

The SQLAlchemy engine logs successful statements that exceed
`DB_SLOW_QUERY_THRESHOLD_SECONDS`. By default, the log includes only duration,
operation type, an SQL fingerprint, and request context. It does not include
SQL text or parameters.

## Production Startup

Gunicorn uses the standalone `uvicorn-worker`. The application access
middleware is the only source of request logs:

```bash
PORT=8000 WEB_CONCURRENCY=2 LOG_LEVEL=info \
  uv run gunicorn -c deploy/gunicorn_conf.py app.main:app
```

Gunicorn writes its error log to stderr and the application writes logs to
stdout.

## API Documentation

The Wiki is the human-readable integration contract. `/docs`, `/redoc`, and
`/openapi.json` are the exact machine-readable contract and online debugging
entry points. Both surfaces cover the same public HTTP operations.

See [`wikis/README.md`](wikis/README.md) for the business documentation index.
It currently covers the three authentication operations and `GET /ping`. When
adding a public operation, use
[`wikis/API_TEMPLATE.md`](wikis/API_TEMPLATE.md) to document its request,
successful response, stable errors, and state side effects.
