from datetime import datetime
from functools import lru_cache

import factory
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthUser, User
from app.models.base import Base, get_local_now
from app.services.auth import (
    DUMMY_CREDENTIAL,
    hash_password,
    normalize_auth_id,
)


TEST_LOGIN_PASSWORD = "test-password-123"


class BaseModelFactory(factory.Factory):
    class Meta:
        abstract = True

    created_at = factory.LazyFunction(get_local_now)
    updated_at = factory.LazyFunction(get_local_now)


class UserFactory(BaseModelFactory):
    class Meta:
        model = User

    name = factory.Faker("name")
    disabled_at = None
    session_version = 1


class AuthUserFactory(BaseModelFactory):
    class Meta:
        model = AuthUser

    user_id = 1
    auth_id = factory.Sequence(lambda number: f"internal.user{number}")
    credential = DUMMY_CREDENTIAL


@lru_cache(maxsize=1)
def _test_login_credential() -> str:
    return hash_password(TEST_LOGIN_PASSWORD)


async def _unique_auth_id(
    db: AsyncSession,
    auth_id: str | None,
) -> str:
    candidate = (
        auth_id
        if auth_id is not None
        else AuthUserFactory.build().auth_id
    )
    normalized = normalize_auth_id(candidate)
    existing_id = await db.scalar(
        select(AuthUser.id).where(AuthUser.auth_id == normalized)
    )
    if existing_id is not None:
        raise ValueError(f"auth_id {normalized!r} already exists")
    return normalized


async def _flush(db: AsyncSession, model: Base) -> None:
    db.add(model)
    await db.flush()


async def build_internal_user(
    db: AsyncSession,
    *,
    auth_id: str | None = None,
    name: str | None = None,
    login: bool = False,
    disabled_at: datetime | None = None,
    session_version: int = 1,
) -> User:
    normalized_auth_id = await _unique_auth_id(db, auth_id)
    values: dict[str, object] = {
        "disabled_at": disabled_at,
        "session_version": session_version,
    }
    if name is not None:
        values["name"] = name

    user = UserFactory.build(**values)
    await _flush(db, user)
    credential = AuthUserFactory.build(
        user_id=user.id,
        auth_id=normalized_auth_id,
        credential=(
            _test_login_credential() if login else DUMMY_CREDENTIAL
        ),
    )
    await _flush(db, credential)
    return user
