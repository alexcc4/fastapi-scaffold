import asyncio
from typing import Optional

import typer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth import pwd_context
from app.db.session import AsyncSessionLocal, close_db_engine
from app.models.user import User, AuthUser


async def create_user_async(
    username: str,
    password: str,
    name: Optional[str] = None
) -> tuple[User, AuthUser]:
    """create user"""
    
    async with AsyncSessionLocal() as session:
        try:
            # check if user already exists
            existing_auth = await session.execute(
                select(AuthUser).where(
                    AuthUser.auth_id == username,
                    AuthUser.auth_type == 1
                )
            )
            if existing_auth.scalar_one_or_none():
                raise ValueError(f"user '{username}' already exists")
            
            # create user record
            user = User(
                name=name or username,
                status=1,
                is_verified=0
            )
            session.add(user)
            await session.flush()  # get user id
            
            # create auth record
            hashed_password = pwd_context.hash(password)
            auth_user = AuthUser(
                user_id=user.id,
                auth_id=username,
                auth_type=1,  # password auth
                credential=hashed_password
            )
            session.add(auth_user)
            
            # commit transaction
            await session.commit()
            await session.refresh(user)
            await session.refresh(auth_user)
            
            return user, auth_user
            
        except IntegrityError as e:
            await session.rollback()
            raise ValueError(f"database constraint error: {str(e)}")
        except Exception as e:
            await session.rollback()
            raise e


def create_user_command(
    username: str = typer.Argument(..., help="username/login name"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="password"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="display name"),
):
    """create new user"""
    
    async def _create():
        try:
            user, auth_user = await create_user_async(username, password, name)
            
            typer.echo(f"✅ user created successfully!")
            typer.echo(f"   ID: {user.id}")
            typer.echo(f"   username: {auth_user.auth_id}")
            typer.echo(f"   display name: {user.name}")
            typer.echo(f"   status: active")
            
        except ValueError as e:
            typer.echo(f"❌ create failed: {e}", err=True)
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"❌ unexpected error: {e}", err=True)
            raise typer.Exit(1)
        finally:
            await close_db_engine()
    
    asyncio.run(_create())
