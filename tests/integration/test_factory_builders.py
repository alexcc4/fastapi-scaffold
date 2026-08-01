from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import AuthUser
from app.services.auth import DUMMY_CREDENTIAL, verify_password
from tests.factories import TEST_LOGIN_PASSWORD, build_internal_user


pytestmark = pytest.mark.integration


async def load_credential(
    db: AsyncSession,
    *,
    user_id: int,
) -> AuthUser:
    credential = await db.scalar(
        select(AuthUser).where(AuthUser.user_id == user_id)
    )
    assert credential is not None
    return credential


async def test_internal_user_builder_flushes_without_committing(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
) -> None:
    disabled_at = datetime(2026, 8, 1, 12, 0, 0)

    user = await build_internal_user(
        db_session,
        auth_id=" Builder.User.Example ",
        name="Builder User",
        disabled_at=disabled_at,
        session_version=3,
    )
    credential = await load_credential(db_session, user_id=user.id)

    assert user.id is not None
    assert user.name == "Builder User"
    assert user.disabled_at == disabled_at
    assert user.session_version == 3
    assert credential.auth_id == "builder.user.example"
    assert credential.credential == DUMMY_CREDENTIAL
    assert not verify_password(
        TEST_LOGIN_PASSWORD,
        credential.credential,
    )
    assert db_session.in_transaction()

    async with db_engine.connect() as connection:
        persisted_id = await connection.scalar(
            select(AuthUser.id).where(AuthUser.auth_id == credential.auth_id)
        )
    assert persisted_id is None


async def test_internal_user_builder_can_create_login_credentials(
    db_session: AsyncSession,
) -> None:
    user = await build_internal_user(
        db_session,
        auth_id="login.user.example",
        login=True,
    )
    credential = await load_credential(db_session, user_id=user.id)

    assert verify_password(TEST_LOGIN_PASSWORD, credential.credential)


async def test_internal_user_builder_rejects_duplicate_auth_id(
    db_session: AsyncSession,
) -> None:
    await build_internal_user(
        db_session,
        auth_id="unique.user.example",
    )

    with pytest.raises(
        ValueError,
        match="auth_id 'unique.user.example' already exists",
    ):
        await build_internal_user(
            db_session,
            auth_id=" Unique.User.Example ",
        )
