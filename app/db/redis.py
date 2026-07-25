from collections.abc import AsyncIterator

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings


settings = get_settings()

redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD.get_secret_value() or None,
    db=settings.REDIS_DB,
    decode_responses=True,
    encoding="utf-8",
)


def create_redis_client() -> Redis:
    return Redis(connection_pool=redis_pool)


async def get_redis() -> AsyncIterator[Redis]:
    client = create_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def close_redis() -> None:
    await redis_pool.aclose()
