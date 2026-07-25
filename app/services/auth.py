import hashlib
import json
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import bcrypt
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.request_context import get_request_context
from app.models import AuthUser, User
from app.models.base import get_local_now


AUTH_LOGGER = logging.getLogger("app.auth")
AUTH_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
TOKEN_PREFIX = "sess_"
SESSION_KEY_PREFIX = "auth:session:"
DUMMY_CREDENTIAL = (
    "$2b$12$ty6YYsI7bCgkpeWQzf3ty.3XgTShOSrSxn/AidP3MDVmLyS9AeJrK"
)


class AuthenticationError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class AccountAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    username: str
    session_fingerprint: str
    token_digest: str


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    user: User
    username: str


@dataclass(frozen=True)
class SessionInspection:
    fingerprint: str
    exists: bool
    user_id: int | None = None
    session_version: int | None = None
    database_version: int | None = None
    ttl_seconds: int | None = None
    created_at: str | None = None


def normalize_auth_id(auth_id: str) -> str:
    normalized = auth_id.strip().lower()
    if not AUTH_ID_PATTERN.fullmatch(normalized):
        raise ValueError(
            "username must be 3-64 lowercase letters, numbers, dots, "
            "underscores, or hyphens"
        )
    return normalized


def normalize_name(name: str) -> str:
    normalized = name.strip()
    if not 1 <= len(normalized) <= 100:
        raise ValueError("name must be 1-100 characters")
    return normalized


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("ascii")


def verify_password(password: str, credential: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            credential.encode("ascii"),
        )
    except (ValueError, UnicodeError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_fingerprint(digest: str) -> str:
    return digest[:12]


def session_key(digest: str) -> str:
    return f"{SESSION_KEY_PREFIX}{digest}"


def _new_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


async def _find_account(
    db: AsyncSession,
    auth_id: str,
    *,
    for_update: bool = False,
) -> tuple[User, AuthUser] | None:
    statement = (
        select(User, AuthUser)
        .join(AuthUser, AuthUser.user_id == User.id)
        .where(AuthUser.auth_id == auth_id)
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await db.execute(statement)).one_or_none()
    if row is None:
        return None
    return row[0], row[1]


async def create_internal_user(
    db: AsyncSession,
    *,
    auth_id: str,
    name: str,
    password: str,
) -> User:
    normalized_auth_id = normalize_auth_id(auth_id)
    normalized_name = normalize_name(name)
    credential = hash_password(password)
    user = User(name=normalized_name)

    try:
        db.add(user)
        await db.flush()
        db.add(
            AuthUser(
                user_id=user.id,
                auth_id=normalized_auth_id,
                credential=credential,
            )
        )
        await db.flush()
    except IntegrityError as exc:
        raise AccountAlreadyExistsError(
            f"account {normalized_auth_id!r} already exists"
        ) from exc

    return user


async def authenticate_internal_user(
    db: AsyncSession,
    redis: Redis,
    *,
    auth_id: str,
    password: str,
) -> IssuedToken:
    try:
        normalized_auth_id = normalize_auth_id(auth_id)
    except ValueError as exc:
        verify_password(password, DUMMY_CREDENTIAL)
        raise AuthenticationError from exc

    account = await _find_account(db, normalized_auth_id)
    credential = account[1].credential if account is not None else DUMMY_CREDENTIAL
    password_matches = verify_password(password, credential)
    if (
        account is None
        or not password_matches
        or account[0].disabled_at is not None
    ):
        raise AuthenticationError

    user = account[0]
    token = _new_token()
    digest = token_digest(token)
    fingerprint = session_fingerprint(digest)
    created_at = get_local_now().isoformat(timespec="seconds")
    payload = {
        "user_id": user.id,
        "session_version": user.session_version,
        "created_at": created_at,
    }
    await redis.set(
        session_key(digest),
        json.dumps(payload, separators=(",", ":")),
        ex=get_settings().AUTH_SESSION_TTL_SECONDS,
    )
    AUTH_LOGGER.info(
        "session_created user_id=%d session_fp=%s",
        user.id,
        fingerprint,
    )
    return IssuedToken(
        access_token=token,
        user=user,
        username=normalized_auth_id,
    )


def _decode_session_payload(raw_payload: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_payload)
        user_id = int(payload["user_id"])
        session_version = int(payload["session_version"])
        created_at = str(payload["created_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AuthenticationError from exc
    return {
        "user_id": user_id,
        "session_version": session_version,
        "created_at": created_at,
    }


async def resolve_session(
    db: AsyncSession,
    redis: Redis,
    token: str,
) -> AuthenticatedSession:
    if not token.startswith(TOKEN_PREFIX):
        raise AuthenticationError

    digest = token_digest(token)
    fingerprint = session_fingerprint(digest)
    key = session_key(digest)
    raw_payload = await redis.get(key)
    if raw_payload is None:
        raise AuthenticationError

    try:
        payload = _decode_session_payload(raw_payload)
    except AuthenticationError:
        await _delete_session_best_effort(
            redis,
            key=key,
            fingerprint=fingerprint,
        )
        raise

    identity_statement = (
        select(User, AuthUser.auth_id)
        .join(AuthUser, AuthUser.user_id == User.id)
        .where(User.id == payload["user_id"])
    )
    identity = (await db.execute(identity_statement)).one_or_none()
    user = identity[0] if identity is not None else None
    if (
        user is None
        or user.disabled_at is not None
        or user.session_version != payload["session_version"]
    ):
        await _delete_session_best_effort(
            redis,
            key=key,
            fingerprint=fingerprint,
            user_id=payload["user_id"],
        )
        AUTH_LOGGER.info(
            "session_rejected user_id=%s session_fp=%s",
            payload["user_id"],
            fingerprint,
        )
        raise AuthenticationError

    context = get_request_context()
    if context is not None:
        context.session_fingerprint = fingerprint
    return AuthenticatedSession(
        user=user,
        username=identity[1],
        session_fingerprint=fingerprint,
        token_digest=digest,
    )


async def _delete_session_best_effort(
    redis: Redis,
    *,
    key: str,
    fingerprint: str,
    user_id: int | None = None,
) -> None:
    try:
        await redis.delete(key)
    except RedisError:
        AUTH_LOGGER.warning(
            "session_cleanup_failed user_id=%s session_fp=%s",
            user_id if user_id is not None else "-",
            fingerprint,
            exc_info=True,
        )


async def logout_session(redis: Redis, session: AuthenticatedSession) -> None:
    await redis.delete(session_key(session.token_digest))
    AUTH_LOGGER.info(
        "session_deleted user_id=%d session_fp=%s",
        session.user.id,
        session.session_fingerprint,
    )


async def reset_internal_password(
    db: AsyncSession,
    *,
    auth_id: str,
    password: str,
) -> User:
    normalized_auth_id = normalize_auth_id(auth_id)
    credential = hash_password(password)
    account = await _find_account(db, normalized_auth_id, for_update=True)
    if account is None:
        raise AccountNotFoundError(
            f"account {normalized_auth_id!r} was not found"
        )
    user, auth_user = account
    auth_user.credential = credential
    user.session_version += 1
    return user


async def set_internal_user_enabled(
    db: AsyncSession,
    *,
    auth_id: str,
    enabled: bool,
) -> User:
    normalized_auth_id = normalize_auth_id(auth_id)
    account = await _find_account(db, normalized_auth_id, for_update=True)
    if account is None:
        raise AccountNotFoundError(
            f"account {normalized_auth_id!r} was not found"
        )
    user = account[0]
    user.disabled_at = None if enabled else get_local_now()
    user.session_version += 1
    return user


async def disable_internal_user(
    db: AsyncSession,
    *,
    auth_id: str,
) -> User:
    return await set_internal_user_enabled(db, auth_id=auth_id, enabled=False)


async def enable_internal_user(
    db: AsyncSession,
    *,
    auth_id: str,
) -> User:
    return await set_internal_user_enabled(db, auth_id=auth_id, enabled=True)


async def inspect_session(
    db: AsyncSession,
    redis: Redis,
    *,
    token: str,
) -> SessionInspection:
    digest = token_digest(token)
    fingerprint = session_fingerprint(digest)
    key = session_key(digest)
    raw_payload = await redis.get(key)
    if raw_payload is None:
        return SessionInspection(fingerprint=fingerprint, exists=False)

    payload = _decode_session_payload(raw_payload)
    ttl_seconds = await redis.ttl(key)
    user = await db.get(User, payload["user_id"])
    return SessionInspection(
        fingerprint=fingerprint,
        exists=True,
        user_id=payload["user_id"],
        session_version=payload["session_version"],
        database_version=user.session_version if user is not None else None,
        ttl_seconds=ttl_seconds,
        created_at=payload["created_at"],
    )
