from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.redis import get_redis, get_token_key
from app.models.user import User
from app.schemas.user import UserResponse
from app.core.deps import verify_clerk_token
from app.core.config import settings


router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=UserResponse)
async def login_or_register(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    response: Response = None
):
    clerk_data = await verify_clerk_token(credentials)
    
    clerk_id = clerk_data["id"]
    email = clerk_data["email_addresses"][0]["email"]
    name = f"{clerk_data['first_name']} {clerk_data['last_name']}"

    query = select(User).where(User.clerk_id == clerk_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    is_new_user = False
    if not user:
        user = User(
            clerk_id=clerk_id,
            email=email,
            name=name,
            status=1
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new_user = True
    
    redis_key = get_token_key(credentials.credentials)
    await redis.set(
        redis_key,
        str(user.id),
        ex=60 * 60 * 24 * settings.TOKEN_EXPIRE_DAYS
    )
    
    if response:
        response.status_code = 201 if is_new_user else 200
    
    return user


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    redis_key = get_token_key(credentials.credentials)
    await redis.delete(redis_key)
    return {"message": "Logged out successfully"}