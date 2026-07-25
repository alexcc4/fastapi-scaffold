from datetime import datetime
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.deps import DbSession
from app.db.redis import get_redis
from app.services.auth import (
    AuthenticatedSession,
    AuthenticationError,
    authenticate_internal_user,
    logout_session,
    resolve_session,
)


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    auto_error=False,
)


class ErrorResponse(BaseModel):
    detail: str


AUTH_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Credentials are invalid or the session has expired",
        "headers": {
            "WWW-Authenticate": {
                "description": "Bearer authentication scheme",
                "schema": {"type": "string", "example": "Bearer"},
            }
        },
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "Session store unavailable",
    },
}


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    name: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(CurrentUserResponse):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


def current_user_response(
    session: AuthenticatedSession,
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=session.user.id,
        username=session.username,
        name=session.user.name,
        created_at=session.user.created_at,
        updated_at=session.user.updated_at,
    )


def unauthorized_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_authenticated_session(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthenticatedSession:
    if token is None:
        raise unauthorized_exception()
    try:
        return await resolve_session(db, redis, token)
    except AuthenticationError as exc:
        raise unauthorized_exception() from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store unavailable",
        ) from exc


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        status.HTTP_200_OK: {
            "headers": {
                "Cache-Control": {
                    "description": "Do not cache token responses",
                    "schema": {"type": "string", "example": "no-store"},
                }
            }
        },
        **AUTH_ERROR_RESPONSES,
    },
    summary="Sign in with an internal account",
)
async def create_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: DbSession,
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenResponse:
    try:
        issued_token = await authenticate_internal_user(
            db,
            redis,
            auth_id=form.username,
            password=form.password,
        )
    except AuthenticationError as exc:
        raise unauthorized_exception() from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store unavailable",
        ) from exc

    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        id=issued_token.user.id,
        username=issued_token.username,
        name=issued_token.user.name,
        created_at=issued_token.user.created_at,
        updated_at=issued_token.user.updated_at,
        access_token=issued_token.access_token,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    responses=AUTH_ERROR_RESPONSES,
    summary="Get the current user",
)
async def get_current_user(
    session: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
) -> CurrentUserResponse:
    return current_user_response(session)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=AUTH_ERROR_RESPONSES,
    summary="Log out of the current session",
)
async def logout(
    session: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> Response:
    try:
        await logout_session(redis, session)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store unavailable",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
