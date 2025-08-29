from typing import Annotated

from fastapi import Depends, HTTPException
from jose import JWTError, jwt, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from sqlalchemy import select

from app.db.session import get_db
from app.db.redis import get_redis
from app.models.user import User as DBUser, AuthUser
from app.core.auth import oauth2_scheme, SECRET_KEY, ALGORITHM, validate_token_in_redis, revoke_token


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
) -> DBUser:
    """get current user - JWT + Redis double verification"""
    
    try:
        # 1. verify JWT format and signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_from_jwt = payload.get("user_id")
        if user_id_from_jwt is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 2. verify redis token
        user_id_from_redis = await validate_token_in_redis(token, redis)
        if user_id_from_redis is None:
            raise HTTPException(
                status_code=401,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 3. ensure JWT and redis user_id match
        if user_id_from_jwt != user_id_from_redis:
            raise HTTPException(
                status_code=401,
                detail="Token user_id mismatch",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 4. query auth user
        auth_result = await db.execute(
            select(AuthUser).where(AuthUser.user_id == user_id_from_redis)
        )
        auth_user = auth_result.scalar_one_or_none()
        
        if not auth_user:
            raise HTTPException(
                status_code=404,
                detail="User not found in database",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = await db.scalar(
            select(DBUser).where(
                DBUser.id == auth_user.user_id,
                DBUser.deleted_at.is_(None)
            )
        )
        
        return user

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )