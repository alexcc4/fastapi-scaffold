import hashlib
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import User
from app.services.auth import (
    AccountAlreadyExistsError,
    create_internal_user,
    disable_internal_user,
    enable_internal_user,
    inspect_session,
    reset_internal_password,
)
from tests.conftest import TEST_PASSWORD, TEST_USERNAME


pytestmark = pytest.mark.integration


async def login(client: AsyncClient, password: str = TEST_PASSWORD) -> str:
    response = await client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_login_stores_only_token_digest(
    unauth_client: AsyncClient,
    auth_user: User,
    redis_client: Redis,
) -> None:
    token = await login(unauth_client)
    digest = hashlib.sha256(token.encode()).hexdigest()
    keys = await redis_client.keys("auth:session:*")

    assert token.startswith("sess_")
    assert len(keys) == 1
    assert keys[0] == f"auth:session:{digest}"
    assert token not in keys[0]
    assert 0 < await redis_client.ttl(keys[0]) <= 604800
    response = await unauth_client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.headers["cache-control"] == "no-store"


async def test_login_and_me_return_frontend_identity_fields(
    unauth_client: AsyncClient,
    auth_user: User,
) -> None:
    login_response = await unauth_client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload == {
        "id": auth_user.id,
        "username": TEST_USERNAME,
        "name": auth_user.name,
        "created_at": auth_user.created_at.isoformat(),
        "updated_at": auth_user.updated_at.isoformat(),
        "access_token": login_payload["access_token"],
        "token_type": "bearer",
    }

    me_response = await unauth_client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {login_payload['access_token']}",
        },
    )

    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": auth_user.id,
        "username": TEST_USERNAME,
        "name": auth_user.name,
        "created_at": auth_user.created_at.isoformat(),
        "updated_at": auth_user.updated_at.isoformat(),
    }


async def test_invalid_credentials_share_one_response(
    unauth_client: AsyncClient,
    auth_user: User,
) -> None:
    wrong_password = await unauth_client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": "wrong-password"},
    )
    unknown_user = await unauth_client.post(
        "/api/auth/token",
        data={"username": "unknown.user", "password": "wrong-password"},
    )
    invalid_username = await unauth_client.post(
        "/api/auth/token",
        data={"username": "x", "password": "wrong-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert invalid_username.status_code == 401
    assert wrong_password.json() == unknown_user.json() == invalid_username.json()


async def test_missing_token_uses_common_unauthorized_response(
    unauth_client: AsyncClient,
) -> None:
    response = await unauth_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired credentials"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_authenticated_client_can_logout(
    client: AsyncClient,
    redis_client: Redis,
) -> None:
    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Scaffold Admin"

    logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert await redis_client.keys("auth:session:*") == []
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_multi_session_and_password_reset_invalidation(
    unauth_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
) -> None:
    first_token = await login(unauth_client)
    second_token = await login(unauth_client)
    assert first_token != second_token

    new_password = "new-test-password-123"
    await reset_internal_password(
        db_session,
        auth_id=TEST_USERNAME,
        password=new_password,
    )
    await db_session.commit()

    for token in (first_token, second_token):
        response = await unauth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
    assert await login(unauth_client, new_password)


async def test_disable_and_enable_invalidate_sessions(
    unauth_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
) -> None:
    old_token = await login(unauth_client)
    await disable_internal_user(db_session, auth_id=TEST_USERNAME)
    await db_session.commit()

    assert (
        await unauth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
    ).status_code == 401
    assert (
        await unauth_client.post(
            "/api/auth/token",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
    ).status_code == 401

    await enable_internal_user(db_session, auth_id=TEST_USERNAME)
    await db_session.commit()
    assert await login(unauth_client)


async def test_stale_session_returns_401_when_cleanup_fails(
    unauth_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
    redis_client: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await login(unauth_client)
    await disable_internal_user(db_session, auth_id=TEST_USERNAME)
    await db_session.commit()
    monkeypatch.setattr(
        redis_client,
        "delete",
        AsyncMock(side_effect=RedisError("delete failed")),
    )

    response = await unauth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


async def test_inspect_session_returns_fingerprint_not_token(
    unauth_client: AsyncClient,
    auth_user: User,
    db_session: AsyncSession,
    redis_client: Redis,
) -> None:
    token = await login(unauth_client)
    inspection = await inspect_session(
        db_session,
        redis_client,
        token=token,
    )

    assert inspection.exists is True
    assert inspection.user_id == auth_user.id
    assert inspection.fingerprint == hashlib.sha256(
        token.encode()
    ).hexdigest()[:12]
    assert token not in repr(inspection)


async def test_auth_table_constraints(
    db_engine: AsyncEngine,
    migrated_database: None,
) -> None:
    async with db_engine.connect() as connection:
        def inspect_constraints(sync_connection):
            inspector = inspect(sync_connection)
            return (
                inspector.get_foreign_keys("auth_users"),
                inspector.get_unique_constraints("auth_users"),
            )

        foreign_keys, unique_constraints = await connection.run_sync(
            inspect_constraints
        )

    assert foreign_keys == []
    assert {
        constraint["name"] for constraint in unique_constraints
    } == {
        "uq_auth_users_auth_id",
        "uq_auth_users_user_id",
    }


async def test_duplicate_internal_account_is_rejected(
    auth_user: User,
    db_session: AsyncSession,
) -> None:
    with pytest.raises(AccountAlreadyExistsError):
        await create_internal_user(
            db_session,
            auth_id=TEST_USERNAME.upper(),
            name="Duplicate Admin",
            password=TEST_PASSWORD,
        )
