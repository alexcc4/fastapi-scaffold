import os   
import sys
import logging
from typing import AsyncGenerator

# hide warnings
logging.getLogger('factory').setLevel(logging.WARNING)
logging.getLogger('factory.generate').setLevel(logging.WARNING)
logging.getLogger('factory.generate.declarations').setLevel(logging.WARNING)
logging.getLogger('faker').setLevel(logging.WARNING)
logging.getLogger('faker.factory').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('aiomysql').setLevel(logging.WARNING)
logging.getLogger('python_multipart').setLevel(logging.WARNING)
logging.getLogger('python_multipart.multipart').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TESTING"] = "1"

import asyncio
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis 
from contextlib import asynccontextmanager

from app.main import app
from app.core.config import settings
from app.models.base import Base
from app.models.user import User, AuthUser
from app.db.session import get_db
from app.db.redis import get_redis, pool 
from app.core.auth import pwd_context
from tests.factories import UserFactory, AuthUserFactory 


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        async with session.begin():
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
    
    async with async_session() as session:
        try:
            from tests.factories import BaseFactory
            BaseFactory._meta.sqlalchemy_session = session

            yield session
        finally:
            try:
                await session.rollback()
            except Exception:
                pass
            finally:
                await session.close()


@asynccontextmanager
async def get_test_redis():
    client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
        encoding='utf-8'
    )
    try:
        yield client
    finally:
        try:
            await client.aclose()
            await asyncio.sleep(0.01) 
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def redis_client() -> AsyncGenerator[Redis, None]:
    async with get_test_redis() as client:
        yield client


@pytest_asyncio.fixture
async def redis_conn():
    redis_client = Redis(connection_pool=pool)
    try:
        yield redis_client
    finally:
        try:
            await redis_client.aclose() 
        except Exception:
            pass



@pytest_asyncio.fixture(scope="function")
async def base_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def client(
    base_client: AsyncClient,
    db_engine: AsyncEngine,
    redis_client: Redis,
) -> AsyncGenerator[AsyncClient, None]:
    old_overrides = app.dependency_overrides.copy()
    
    try:
        async def override_get_db():
            async_session = async_sessionmaker(
                bind=db_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            async with async_session() as session:
                try:
                    yield session
                finally:
                    try:
                        await session.rollback()
                    except Exception:
                        pass
                    finally:
                        await session.close()

        async def override_get_redis():
            yield redis_client
            
            
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_redis] = override_get_redis
        yield base_client
    finally:
        app.dependency_overrides = old_overrides



async def create_test_user(
    db: AsyncSession, 
    auth_id: str = "testuser", 
    password: str = "test123",
) -> tuple[User, AuthUser]:
    """create test user"""
    user = await db.run_sync(lambda session:
        UserFactory.build(name=auth_id)
    )
    db.add(user)
    await db.flush()
    
    auth_user = await db.run_sync(lambda session:
        AuthUserFactory.build(
            user_id=user.id,
            auth_id=auth_id,
            auth_type=1,
            credential=pwd_context.hash(password)
        )
    )
    db.add(auth_user)
    
    await db.commit()
    return user, auth_user


async def login_test_user(client: AsyncClient, auth_id: str = "testuser", password: str = "test123") -> str:
    """login test user and return token"""
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": auth_id, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]