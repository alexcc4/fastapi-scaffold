from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction

from app.api.auth import get_authenticated_session
from app.api.deps import DbSession
from app.models import AuthUser
from app.services.auth import (
    AccountAlreadyExistsError,
    AuthenticatedSession,
    create_internal_user,
)
from tests.conftest import TEST_USERNAME


pytestmark = pytest.mark.integration

PROBE_PASSWORD = "probe-password-123"
COMMITTED_USERNAME = "probe.committed"
ROLLED_BACK_USERNAME = "probe.rolled.back"
COMMIT_FAIL_USERNAME = "probe.commit.fail"


async def account_exists(engine: AsyncEngine, auth_id: str) -> bool:
    statement = select(AuthUser.id).where(AuthUser.auth_id == auth_id)
    async with engine.connect() as connection:
        return (await connection.execute(statement)).scalar_one_or_none() is not None


async def test_authenticated_request_can_write(
    live_app: FastAPI,
    live_client: AsyncClient,
    db_engine: AsyncEngine,
) -> None:
    @live_app.post("/probe/write")
    async def write(
        _session: Annotated[
            AuthenticatedSession,
            Depends(get_authenticated_session),
        ],
        db: DbSession,
    ) -> dict[str, int]:
        user = await create_internal_user(
            db,
            auth_id=COMMITTED_USERNAME,
            name="Probe Committed",
            password=PROBE_PASSWORD,
        )
        return {"id": user.id}

    response = await live_client.post("/probe/write")

    assert response.status_code == 200
    assert response.json()["id"] > 0
    assert await account_exists(db_engine, COMMITTED_USERNAME)


async def test_failed_request_does_not_persist_writes(
    live_app: FastAPI,
    live_client: AsyncClient,
    db_engine: AsyncEngine,
) -> None:
    @live_app.post("/probe/write-then-fail")
    async def write_then_fail(
        _session: Annotated[
            AuthenticatedSession,
            Depends(get_authenticated_session),
        ],
        db: DbSession,
    ) -> None:
        await create_internal_user(
            db,
            auth_id=ROLLED_BACK_USERNAME,
            name="Probe Rolled Back",
            password=PROBE_PASSWORD,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="probe failure after write",
        )

    response = await live_client.post("/probe/write-then-fail")

    assert response.status_code == 409
    assert not await account_exists(db_engine, ROLLED_BACK_USERNAME)


async def test_service_error_maps_to_status_without_breaking_teardown(
    live_app: FastAPI,
    live_client: AsyncClient,
) -> None:
    @live_app.post("/probe/duplicate")
    async def duplicate(
        _session: Annotated[
            AuthenticatedSession,
            Depends(get_authenticated_session),
        ],
        db: DbSession,
    ) -> None:
        try:
            await create_internal_user(
                db,
                auth_id=TEST_USERNAME,
                name="Duplicate Probe",
                password=PROBE_PASSWORD,
            )
        except AccountAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="account already exists",
            ) from exc

    response = await live_client.post("/probe/duplicate")

    assert response.status_code == 409


async def test_commit_failure_does_not_return_success(
    live_app: FastAPI,
    live_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @live_app.post("/probe/commit-fail")
    async def commit_fail(
        _session: Annotated[
            AuthenticatedSession,
            Depends(get_authenticated_session),
        ],
        db: DbSession,
    ) -> dict[str, bool]:
        await create_internal_user(
            db,
            auth_id=COMMIT_FAIL_USERNAME,
            name="Probe Commit Fail",
            password=PROBE_PASSWORD,
        )
        return {"ok": True}

    # begin().__aexit__ commits on success. Patch that boundary so flush() still
    # works, while the request-ending commit fails. With scope="function" this
    # happens before the response is sent.
    original_aexit = AsyncSessionTransaction.__aexit__

    async def failing_aexit(self, type_, value, traceback):
        if type_ is None:
            exc = RuntimeError("commit failed")
            await original_aexit(self, RuntimeError, exc, None)
            raise exc
        return await original_aexit(self, type_, value, traceback)

    monkeypatch.setattr(AsyncSessionTransaction, "__aexit__", failing_aexit)

    async with AsyncClient(
        transport=ASGITransport(
            app=live_app,
            raise_app_exceptions=False,
        ),
        base_url="http://test",
        headers=live_client.headers,
    ) as client:
        response = await client.post("/probe/commit-fail")

    assert response.status_code >= 500
