"""
Debug API Tests

Note: For SQLAlchemy AsyncSession usage in tests:
1. Test code uses one session (via db fixture)
2. API requests automatically use new sessions (created in client fixture)
3. Test code can continue using the original session

For more information see documentation links in conftest.py.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from redis.asyncio import Redis
from sqlalchemy import select


async def test_echo(base_client: AsyncClient, test_token: str):
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
    redis_conn: Redis,
    fake_user
):
    user = User(**fake_user())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await redis_conn.set("test", "hello")
    
    response = await client.get("/api/v1/debug/db_echo")
    assert response.status_code == 200
    data = response.json()
    assert data["user_count"] >= 1
    assert data["redis_value"] == "hello"

    val = await redis_conn.get("test")
    assert val == "hello"
    
    result = await db.execute(
        select(User).where(User.id == user.id)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.id == user.id
