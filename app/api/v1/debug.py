from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.redis import get_redis
from app.models.user import User
from app.core.deps import get_db


router = APIRouter()


class EchoMessage(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str
    user_id: int


@router.post("/echo", response_model=EchoResponse)
async def echo(
    msg: EchoMessage,
):
    return {
        "message": msg.message,
        "user_id": 1234
    }


@router.get("/db_echo")
async def db_echo(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    # Get user count
    user_count = await db.scalar(
        select(func.count()).select_from(User)
    )
    
    # Get redis value
    redis_value = await redis.get("test")

    return {
        "user_count": user_count or 0,
        "redis_value": redis_value
    }

