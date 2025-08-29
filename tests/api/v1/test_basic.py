from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.user import User
from tests.conftest import create_test_user


async def test_mysql_basic(db: AsyncSession):
    """Test basic MySQL operations."""
    result = await db.execute(text("SELECT 1"))
    row = result.scalar()
    assert row == 1


async def test_mysql_orm_insert_and_query(db: AsyncSession):
    """Test ORM insert and query operations."""
    test_user, _ = await create_test_user(db)
    result = await db.get(User, test_user.id)
    assert result is not None


async def test_redis_basic(redis_conn: Redis):
    """Test basic Redis operations."""
    # String operations
    await redis_conn.set("test_key", "test_value")
    value = await redis_conn.get("test_key")
    assert value == "test_value"
