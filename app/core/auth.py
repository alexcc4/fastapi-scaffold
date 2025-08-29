from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.config import settings
from app.db.session import AsyncSession
from app.models.user import User as DBUser, AuthUser

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_DAYS = settings.JWT_EXPIRE_DAYS
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str   :
    """create access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def store_token_in_redis(token: str, user_id: int, redis: Redis) -> None:
    """store token in redis"""
    ttl_seconds = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 
    await redis.set(f"auth_token:{token}", str(user_id), ex=ttl_seconds)


async def validate_token_in_redis(token: str, redis: Redis) -> Optional[int]:
    """validate token in redis and return user_id"""
    user_id_str = await redis.get(f"auth_token:{token}")
    if user_id_str:
        return int(user_id_str)
    return None


async def revoke_token(token: str, redis: Redis) -> None    :
    """revoke token"""
    await redis.delete(f"auth_token:{token}")


async def authenticate_user(
    auth_id: str, 
    auth_type: int, 
    db: AsyncSession, 
    redis: Redis,
    credential: Optional[str] = None 
) -> DBUser:
    """authentication entry point - return user with token
    """
    if auth_type == 1:
        # internal account password login
        if not credential:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user_id = await authenticate_internal_user(auth_id, credential, db)
    else:
        raise HTTPException(status_code=401, detail="Invalid auth type")
    
    # complete authentication process: generate token and store
    return await complete_authentication(user_id, db, redis)


async def complete_authentication(user_id: int, db: AsyncSession, redis: Redis) -> tuple[DBUser, str]:
    """complete authentication process: generate token and store to Redis"""
    # 1. generate JWT token
    payload = {'user_id': user_id}
    token = create_access_token(payload)
    
    # 2. store to Redis
    await store_token_in_redis(token, user_id, redis)
    
    # 3. get full user info
    user = await db.scalar(
        select(DBUser).where(
            DBUser.id == user_id,   
            DBUser.deleted_at.is_(None)
        )   
    )
    
    return user, token

async def authenticate_internal_user(auth_id: str, credential: str, db: AsyncSession) -> int:
    """internal account password login - only authenticate, return user_id"""
    result = await db.execute(
        select(AuthUser).where(
            AuthUser.auth_id == auth_id,
            AuthUser.auth_type == 1
        )
    )
    auth_user = result.scalar_one_or_none()
    
    if not auth_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # verify password
    if not pwd_context.verify(credential, auth_user.credential):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return auth_user.user_id


async def logout_user(token: str, redis: Redis):
    """logout user"""
    await revoke_token(token, redis)