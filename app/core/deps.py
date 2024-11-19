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
    
    session_id = credentials.credentials
    if not session_id:
        raise AuthenticationError("Invalid session_id")

    try:
        async with httpx.AsyncClient() as client:
            session_response = await client.get(
                f"{settings.CLERK_API_URL}/sessions/{session_id}",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if session_response.status_code != 200:
                raise AuthenticationError("Invalid session")

            session_data = session_response.json()
            if session_data.get("status") != "active":
                raise AuthenticationError("Session is not active")

            user_id = session_data.get("user_id")

            user_response = await client.get(
                f"{settings.CLERK_API_URL}/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if user_response.status_code != 200:
                raise AuthenticationError("Failed to fetch user info")

            return user_response.json()
            
    except httpx.RequestError:
        raise AuthenticationError("Failed to verify token")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> User:
    session_id = credentials.credentials
    redis_key = get_token_key(session_id)
    
    user_id = await redis.get(redis_key)
    if user_id:
        query = select(User).where(User.id == int(user_id))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if user:
            return user
    
    raise AuthenticationError("Invalid session_id")
