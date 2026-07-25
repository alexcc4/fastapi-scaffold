import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import typer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import close_database, session_factory
from app.db.redis import close_redis, create_redis_client
from app.services.auth import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AuthenticationError,
    create_internal_user,
    disable_internal_user,
    enable_internal_user,
    inspect_session,
    reset_internal_password,
)


cli = typer.Typer(no_args_is_help=True)


async def _run_with_database(
    operation: Callable[[AsyncSession], Awaitable[Any]],
) -> Any:
    try:
        async with session_factory.begin() as db:
            return await operation(db)
    finally:
        await close_database()


async def _run_with_database_and_redis(
    operation: Callable[[AsyncSession, Redis], Awaitable[Any]],
) -> Any:
    redis = create_redis_client()
    try:
        async with session_factory.begin() as db:
            return await operation(db, redis)
    finally:
        await redis.aclose()
        await close_redis()
        await close_database()


def _password_prompt() -> str:
    return typer.prompt(
        "Password",
        hide_input=True,
        confirmation_prompt=True,
    )


def _exit_with_error(exc: Exception) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=1)


@cli.command("create-user")
def create_user_command(
    username: str,
    name: str = typer.Option(..., "--name"),
) -> None:
    password = _password_prompt()

    async def operation(db: AsyncSession) -> Any:
        return await create_internal_user(
            db,
            auth_id=username,
            name=name,
            password=password,
        )

    try:
        user = asyncio.run(_run_with_database(operation))
    except (AccountAlreadyExistsError, ValueError) as exc:
        _exit_with_error(exc)
    typer.echo(f"Created user id={user.id} username={username.lower()}")


@cli.command("reset-password")
def reset_password_command(username: str) -> None:
    password = _password_prompt()

    async def operation(db: AsyncSession) -> Any:
        return await reset_internal_password(
            db,
            auth_id=username,
            password=password,
        )

    try:
        user = asyncio.run(_run_with_database(operation))
    except (AccountNotFoundError, ValueError) as exc:
        _exit_with_error(exc)
    typer.echo(f"Reset password for user id={user.id}")


@cli.command("disable-user")
def disable_user_command(username: str) -> None:
    async def operation(db: AsyncSession) -> Any:
        return await disable_internal_user(db, auth_id=username)

    try:
        user = asyncio.run(_run_with_database(operation))
    except (AccountNotFoundError, ValueError) as exc:
        _exit_with_error(exc)
    typer.echo(f"Disabled user id={user.id}")


@cli.command("enable-user")
def enable_user_command(username: str) -> None:
    async def operation(db: AsyncSession) -> Any:
        return await enable_internal_user(db, auth_id=username)

    try:
        user = asyncio.run(_run_with_database(operation))
    except (AccountNotFoundError, ValueError) as exc:
        _exit_with_error(exc)
    typer.echo(f"Enabled user id={user.id}")


@cli.command("inspect-session")
def inspect_session_command() -> None:
    token = typer.prompt("Token", hide_input=True)

    async def operation(db: AsyncSession, redis: Redis) -> Any:
        return await inspect_session(db, redis, token=token)

    try:
        inspection = asyncio.run(_run_with_database_and_redis(operation))
    except (AuthenticationError, ValueError) as exc:
        _exit_with_error(exc)

    typer.echo(f"session_fp={inspection.fingerprint}")
    typer.echo(f"exists={str(inspection.exists).lower()}")
    if inspection.exists:
        typer.echo(f"user_id={inspection.user_id}")
        typer.echo(f"session_version={inspection.session_version}")
        typer.echo(f"database_version={inspection.database_version}")
        typer.echo(f"ttl_seconds={inspection.ttl_seconds}")
        typer.echo(f"created_at={inspection.created_at}")


if __name__ == "__main__":
    cli()
