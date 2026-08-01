import os
from collections.abc import AsyncIterator

os.environ["APP_ENV"] = "test"

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.db.mysql import close_database, get_db
from app.db.redis import close_redis, get_redis
from app.main import app, create_app
from app.models import AuthUser, User
from tests.factories import TEST_LOGIN_PASSWORD, build_internal_user


TEST_USERNAME = "scaffold.admin"
TEST_PASSWORD = TEST_LOGIN_PASSWORD


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    settings = get_settings()
    if settings.APP_ENV != "test":
        pytest.exit("APP_ENV must be test before running pytest")
    return settings


@pytest.fixture(scope="session")
def safe_integration_settings(test_settings: Settings) -> Settings:
    if not test_settings.DB_NAME.startswith("test_"):
        pytest.exit("integration tests require DB_NAME to start with test_")
    if test_settings.REDIS_DB == 0:
        pytest.exit("integration tests require a disposable non-zero REDIS_DB")
    return test_settings


@pytest.fixture(scope="session")
def migrated_database(
    safe_integration_settings: Settings,
) -> None:
    command.downgrade(Config("alembic.ini"), "base")
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def base_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def db_engine(
    safe_integration_settings: Settings,
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        safe_integration_settings.database_url,
        poolclass=NullPool,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
    migrated_database: None,
) -> AsyncIterator[AsyncSession]:
    session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
    )
    async with db_engine.begin() as connection:
        await connection.execute(delete(AuthUser))
        await connection.execute(delete(User))

    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with db_engine.begin() as connection:
        await connection.execute(delete(AuthUser))
        await connection.execute(delete(User))


@pytest_asyncio.fixture
async def redis_client(
    safe_integration_settings: Settings,
) -> AsyncIterator[Redis]:
    client = Redis(
        host=safe_integration_settings.REDIS_HOST,
        port=safe_integration_settings.REDIS_PORT,
        password=(
            safe_integration_settings.REDIS_PASSWORD.get_secret_value() or None
        ),
        db=safe_integration_settings.REDIS_DB,
        decode_responses=True,
    )
    await client.ping()
    await client.flushdb()
    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def test_app(
    db_session: AsyncSession,
    redis_client: Redis,
) -> AsyncIterator[FastAPI]:
    app_under_test = create_app()

    async def override_db() -> AsyncIterator[AsyncSession]:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    async def override_redis() -> AsyncIterator[Redis]:
        yield redis_client

    app_under_test.dependency_overrides[get_db] = override_db
    app_under_test.dependency_overrides[get_redis] = override_redis
    try:
        yield app_under_test
    finally:
        app_under_test.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def auth_user(db_session: AsyncSession) -> User:
    user = await build_internal_user(
        db_session,
        auth_id=TEST_USERNAME,
        name="Scaffold Admin",
        login=True,
    )
    # Production-wired clients use an independent database Session.
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def client(
    unauth_client: AsyncClient,
    auth_user: User,
) -> AsyncIterator[AsyncClient]:
    response = await unauth_client.post(
        "/api/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    unauth_client.headers["Authorization"] = (
        f"Bearer {response.json()['access_token']}"
    )
    try:
        yield unauth_client
    finally:
        unauth_client.headers.pop("Authorization", None)


@pytest_asyncio.fixture
async def live_app(
    db_session: AsyncSession,
    redis_client: Redis,
) -> AsyncIterator[FastAPI]:
    # Exercises the production get_db / get_redis wiring with no overrides.
    # Dispose between tests so QueuePool connections are not reused across
    # pytest-asyncio function-scoped event loops.
    await close_database()
    await close_redis()
    try:
        yield create_app()
    finally:
        await close_database()
        await close_redis()


@pytest_asyncio.fixture
async def live_client(
    live_app: FastAPI,
    auth_user: User,
) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=live_app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.post(
            "/api/auth/token",
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200
        test_client.headers["Authorization"] = (
            f"Bearer {response.json()['access_token']}"
        )
        yield test_client
