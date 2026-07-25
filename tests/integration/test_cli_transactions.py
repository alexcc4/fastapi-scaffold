import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.cli import _run_with_database
from app.models import AuthUser
from app.services.auth import create_internal_user


pytestmark = pytest.mark.integration

CLI_PASSWORD = "cli-password-123"


async def account_exists(engine: AsyncEngine, auth_id: str) -> bool:
    statement = select(AuthUser.id).where(AuthUser.auth_id == auth_id)
    async with engine.connect() as connection:
        return (await connection.execute(statement)).scalar_one_or_none() is not None


async def test_run_with_database_commits_on_success(
    db_session,
    db_engine: AsyncEngine,
) -> None:
    auth_id = "cli.commit.ok"

    async def operation(db):
        return await create_internal_user(
            db,
            auth_id=auth_id,
            name="CLI Commit",
            password=CLI_PASSWORD,
        )

    user = await _run_with_database(operation)

    assert user.id is not None
    assert await account_exists(db_engine, auth_id)


async def test_run_with_database_rolls_back_on_error(
    db_session,
    db_engine: AsyncEngine,
) -> None:
    auth_id = "cli.rollback.fail"

    async def operation(db):
        await create_internal_user(
            db,
            auth_id=auth_id,
            name="CLI Rollback",
            password=CLI_PASSWORD,
        )
        raise RuntimeError("force rollback")

    with pytest.raises(RuntimeError, match="force rollback"):
        await _run_with_database(operation)

    assert not await account_exists(db_engine, auth_id)
