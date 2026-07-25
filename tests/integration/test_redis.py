import pytest
from redis.asyncio import Redis


@pytest.mark.integration
async def test_redis_connection(redis_client: Redis) -> None:
    await redis_client.set("scaffold:test", "ok")

    assert await redis_client.get("scaffold:test") == "ok"
