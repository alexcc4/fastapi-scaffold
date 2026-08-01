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
- Prefer Typer for user-facing and operations-facing Python CLIs. Keep
  multi-command entry points as command groups, and cover `--help`, exit codes,
  and sensitive input with `CliRunner`.

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
- The Wiki is the human-readable integration contract and OpenAPI is the exact
  machine-readable contract. They must cover the same public HTTP operations.
  Give each operation its own level-two section with a business-action title,
  followed by `- URL:` and `- Method:` metadata with inline-code values and an
  uppercase method. Follow `wikis/API_TEMPLATE.md` for the complete contract.
- Every operation section must describe request fields. When OpenAPI declares
  a request body, include a JSON or form example; otherwise write
  `Request body: none`. Document the success status and a complete response
  example; when there is no body, write `Response body: none`. Add a complete
  request only for service-to-service operations where it has genuine
  integration value; do not duplicate curl for ordinary frontend APIs.
- Sensitive values in operation example blocks may only use `<password>`,
  `<new-password>`, and `<opaque-token>`. Usernames must match
  `[a-z0-9._-]+\.example`. Never include fixed test credentials, real tokens,
  or secrets.
- The automated documentation gate must compare Wiki operations with the
  current OpenAPI document and validate operation metadata, request and
  response examples, and sensitive placeholders. Response examples must stay
  synchronized with their response models.
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
- Prefer high-level asynchronous Builders from `tests/factories.py` for test
  arrangement. Exercise behavior through public HTTP or an explicit service
  seam. When account creation, CLI transactions, duplicate accounts, or other
  production behavior is part of the test narrative, continue to call the
  corresponding production entry point.
- Factories remain build-only. Builders call only `add()` and `flush()` and do
  not commit by default.
- Test setup may commit only when using an independent Session or verifying
  cross-transaction visibility. Explain the reason at the call site.
- Use raw SQL only for fault injection or independent persistence and
  transaction verification, not for ordinary test-data setup.
- `uv run pytest -m "not integration"` provides fast feedback but does not
  replace the complete test suite.

Before committing, run at least:

```bash
uv run pytest
APP_ENV=test uv run alembic heads
git diff --check
```
