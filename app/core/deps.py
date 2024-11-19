from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
import httpx

from app.db.session import get_db
from app.db.redis import get_redis, get_token_key
from app.models.user import User
from app.core.exceptions import AuthenticationError
from app.core.config import settings


security = HTTPBearer()


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials,
) -> dict:
    if not credentials:
        raise AuthenticationError("No credentials provided")
    
    token = credentials.credentials
    if not token:
        raise AuthenticationError("Invalid token format")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.CLERK_API_URL}/users/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Invalid token")
            
            return response.json()
    except httpx.RequestError:
        raise AuthenticationError("Failed to verify token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    redis_key = get_token_key(token)
    
    user_id = await redis.get(redis_key)
    if user_id:
        query = select(User).where(User.id == int(user_id))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if user:
            return user
    
    raise AuthenticationError("Invalid or expired token")
