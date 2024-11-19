"""
Test Configuration File

About SQLAlchemy AsyncSession usage and best practices:
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- https://docs.sqlalchemy.org/en/20/orm/session_basics.html#session-basics-external-transaction

About FastAPI testing:
- https://fastapi.tiangolo.com/tutorial/testing/
- https://fastapi.tiangolo.com/advanced/testing-database/

SQLAlchemy sessions are one-shot and cannot be reused in different contexts.
Each API request should use a new session instead of reusing existing ones.
This is why we create new sessions for each request in the client fixture.

Related discussions:
- https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#session-external-transaction
- https://pytest-asyncio.readthedocs.io/en/latest/
"""

import os
os.environ["TESTING"] = "1"  # Enable testing mode


import asyncio
import pytest
import pytest_asyncio
from typing import Any, Callable, Generator, AsyncGenerator
from redis.asyncio import Redis, ConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from fastapi import HTTPException
from faker import Faker

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.core.deps import get_redis, get_db
from app.db.redis import pool
from app.core.config import settings


fake = Faker()

print(settings.DATABASE_URL)
print(settings.REDIS_URL)


@pytest.fixture(scope="session")
def event_loop():
    """Create and provide a new event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop


@pytest.fixture(scope="session")
async def redis_client():
    pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        encoding="utf-8",
        max_connections=10
    )
    redis_client = Redis(connection_pool=pool)
    yield redis_client
    await redis_client.close()
    await pool.disconnect()

@pytest.fixture
async def redis_conn():
    redis_client = Redis(connection_pool=pool)
    try:
        yield redis_client
    finally:
        await redis_client.close()

@pytest_asyncio.fixture(scope="session")
async def engine(): 
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db(engine):
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

@pytest_asyncio.fixture
async def base_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def client(
    base_client: AsyncClient,
    engine,
    redis_conn: Redis,
) -> AsyncGenerator[AsyncClient, None]:
    old_overrides = app.dependency_overrides.copy()
    
    try:
        async def override_get_db():
            async_session = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            async with async_session() as session:
                try:
                    yield session
                finally:
                    await session.rollback()
                    await session.close()

        async def override_get_redis():
            yield redis_conn

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_redis] = override_get_redis
        
        yield base_client
    finally:
        app.dependency_overrides = old_overrides

@pytest.fixture
def test_token() -> str:
    """Provide a test token."""
    return "test_token"

@pytest_asyncio.fixture
async def test_user(db: AsyncSession, fake_user: dict) -> User:
    """Create a test user in database."""
    user = User(**fake_user())
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
def fake_user() -> Callable[[dict | None], dict]:
    def create_fake_user(clerk_data: dict | None = None) -> dict:
        if clerk_data:
            return {
                "clerk_id": clerk_data["id"],
                "email": clerk_data["email_addresses"][0]["email"],
                "name": f"{clerk_data['first_name']} {clerk_data['last_name']}"
            }
        return {
            "clerk_id": fake.pystr(10),
            "email": fake.email(),
            "name": fake.name(),
        }
    return create_fake_user

@pytest.fixture
def fake_clerk() -> dict:
    """
    Mock a Clerk user for testing
    """
    return {
        "id": fake.pystr(10),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email_addresses": [
            {
                "email": fake.email(),
            }
        ]
    }


@pytest.fixture(scope="function")
async def mock_clerk_success(mocker, fake_clerk):
    """Mock successful Clerk token verification."""
    mock = mocker.patch('app.api.v1.auth.verify_clerk_token', new_callable=AsyncMock)
    mock.return_value = fake_clerk
    return mock

@pytest.fixture(scope="function")
async def mock_clerk_failure(mocker):
    """Mock failed Clerk token verification."""
    mock = mocker.patch('app.api.v1.auth.verify_clerk_token', new_callable=AsyncMock)
    mock.side_effect = HTTPException(status_code=401, detail="Invalid token")
    return mock

@pytest.fixture(scope="function")
def auth_headers(test_token):
    """Provide authentication headers."""
    return {"Authorization": f"Bearer {test_token}"}
