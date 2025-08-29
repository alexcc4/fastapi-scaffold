from httpx import AsyncClient
from sqlalchemy import select
from redis.asyncio import Redis

from app.models.user import User
from app.db.session import AsyncSession
from tests.conftest import create_test_user



async def test_echo(base_client: AsyncClient):
    response = await base_client.post(
        "/api/v1/debug/echo",
        json={"message": "hello"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "hello"
    assert data["user_id"] == 1234


async def test_db_echo(
    client: AsyncClient,
    db: AsyncSession,
    redis_client: Redis 
):
    test_user, _ = await create_test_user(db)
    
    await redis_client.set("test", "hello")
    
    response = await client.get("/api/v1/debug/db_echo")
    assert response.status_code == 200

    val = await redis_client.get("test")
    assert val == "hello"
    
    result = await db.execute(
        select(User).where(User.id == test_user.id)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.id == test_user.id
