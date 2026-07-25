# AGENTS.md

This file contains only long-lived engineering constraints. See `README.md`
for installation, startup, and migration commands. Business API documentation
belongs in `wikis/`.

## Principles

- Define the scope and success criteria before implementation. Change only
  what the current task requires.
- Choose the smallest implementation that solves the current problem. Do not
  add compatibility layers, configuration options, or abstractions in advance.
- Reproduce defects before fixing them, then verify the fix. Preserve existing
  user changes.
- Run every Python command through `uv run` and manage dependencies with
  `uv add`.
- Do not pin dependencies with exact `==` versions. Commit `uv.lock`.

## Layering

- `app/api/`: HTTP routes, dependency injection, request validation, and
  status codes.
- `app/core/`: Application-wide cross-cutting concerns such as configuration.
- `app/db/`: MySQL and Redis connection and session infrastructure.
- `app/models/`: SQLAlchemy ORM models.
- Create `app/services/` only after reusable domain logic has clearly emerged
  across modules.

Dependencies flow from `api` to `core`, `db`, and `models`. Models must not
depend on the API layer.

## Data and Migrations

- Use SQLAlchemy 2.0 `Mapped` and `mapped_column`. Models inherit from
  `app.models.base.Base`.
- Import every new model in `app/models/__init__.py` so Alembic can discover
  its metadata.
- Do not create database foreign keys between tables. Application logic
  maintains referential integrity.
- Store database timestamps as timezone-naive `Asia/Shanghai` local time.
- Every database schema change requires an Alembic migration. Never modify a
  historical migration.
- Use English for Alembic revision messages and migration filenames.
- Load configuration from `.env.{APP_ENV}` or environment variables. Never
  commit real environment files or secrets.

## Transactions

The entry adapter owns the transaction. One request or command corresponds to
one transaction.

- `get_db` in `app/db/mysql.py` and `session_factory.begin()` in the CLI are
  the only transaction boundaries.
- HTTP injection must use `app.api.deps.DbSession`, never a bare
  `Depends(get_db)`. `DbSession` fixes `scope="function"` so the commit occurs
  before the response is sent. Scope participates in FastAPI's dependency
  cache key, so mixing scopes creates two sessions and two transactions in one
  request.
- A `StreamingResponse` that queries the database while streaming cannot use
  `DbSession` directly. Design its session lifecycle separately.
- A new yield dependency that depends on `DbSession` must also declare
  `scope="function"`. Otherwise FastAPI raises an expected startup error.
- Services never call `begin()`, `commit()`, or `rollback()`. They only query,
  acquire row locks, modify state, and call `flush()` when necessary.
- When a service translates a unique-constraint violation into a domain
  exception, it must call `flush()` inside the service. Otherwise the
  `IntegrityError` is deferred until the entry adapter commits and cannot be
  translated there.
- A session cannot be committed after `flush()` fails. A route that catches a
  service exception must raise `HTTPException`; it must not swallow the
  exception and return normally, or the entry commit will turn the intended
  4xx response into a 500.

## APIs and Documentation

- Configure CORS origins explicitly and keep `allow_credentials=False`.
- The scaffold provides only the minimum authentication foundation needed for
  internal username/password accounts, opaque tokens, and account
  enable/disable operations. It does not include RBAC, SSO, refresh tokens, or
  an application-specific user system.
- OpenAPI is the exact machine-readable API contract. Core frontend integration
  endpoints may document complete requests, successful responses, error
  statuses, and representative JSON examples in `wikis/`.
- Keep Wiki examples synchronized with the current response models and tests.
  Never include fixed test credentials, real tokens, or secrets.
- `wikis/README.md` is the business documentation index. Update it whenever a
  new topic document is added.

## Testing

- `uv run pytest` runs real MySQL, Redis, and Alembic integration tests by
  default.
- MySQL tests may connect only to a disposable database whose name starts with
  `test_`.
- Redis tests may connect only to a disposable nonzero database and must run
  `FLUSHDB` before and after each test.
- Tests must fail when infrastructure connections fail. Never skip them
  automatically.
- For fast feedback, run `uv run pytest -m "not integration"`, but this does
  not replace the complete test suite.

Before committing, run at least:

```bash
uv run pytest
APP_ENV=test uv run alembic heads
git diff --check
```
