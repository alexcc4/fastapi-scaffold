from typing import AsyncGenerator

from redis.asyncio import Redis, ConnectionPool
from fastapi import Depends

from app.core.config import settings


pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    encoding="utf-8",
    max_connections=10
)


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose() 


async def get_redis_client(redis: Redis = Depends(get_redis)) -> Redis:
    return redis
