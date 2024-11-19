import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from httpx import AsyncClient
from app.models.user import User


async def test_mysql_basic(db: AsyncSession):
    """Test basic MySQL operations."""
    result = await db.execute(text("SELECT 1"))
    row = result.scalar()
    assert row == 1


async def test_mysql_orm_insert_and_query(db: AsyncSession, test_user: User):
    """Test ORM insert and query operations."""
    # 查询用户
    result = await db.get(User, test_user.id)
    assert result is not None


async def test_redis_basic(redis_conn: Redis):
    """Test basic Redis operations."""
    # String operations
    await redis_conn.set("test_key", "test_value")
    value = await redis_conn.get("test_key")
    assert value == "test_value"
