import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.integration
async def test_mysql_connection(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as connection:
        assert await connection.scalar(text("SELECT 1")) == 1
