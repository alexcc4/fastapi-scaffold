from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.slow_query import install_slow_query_logging


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)
install_slow_query_logging(
    engine.sync_engine,
    threshold_seconds=settings.DB_SLOW_QUERY_THRESHOLD_SECONDS,
)
session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory.begin() as session:
        yield session


async def close_database() -> None:
    await engine.dispose()
