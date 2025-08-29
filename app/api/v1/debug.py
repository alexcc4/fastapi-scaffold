from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.schemas.echo import EchoMessage, EchoResponse


router = APIRouter()


@router.post("/echo", response_model=EchoResponse)
async def echo(
    msg: EchoMessage,
):
    return EchoResponse(
        message=msg.message,
        user_id=1234
    )


@router.get("/db_echo")
async def db_echo(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    user_count = await db.scalar(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )
    
    redis_value = await redis.get("test")

    return EchoResponse(
        message=f"user_count: {user_count or 0}, redis_value: {redis_value}",
        user_id=1234
    )

