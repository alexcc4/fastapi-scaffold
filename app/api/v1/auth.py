from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.redis import get_redis
from app.models.user import User as DBUser
from app.schemas.auth import LoginRequest, LoginResponse
from app.core.auth import authenticate_user, logout_user, oauth2_scheme
from app.core.deps import get_current_user
from app.schemas.user import UserResponse


router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    """standard OAuth2 token endpoint - only support internal account password login"""
    
    # OAuth2 standard endpoint only supports internal account password login
    auth_type = 1
    
    
    _, token = await authenticate_user(
            auth_id=form_data.username,
            auth_type=auth_type,
            db=db,
            redis=redis,
            credential=form_data.password
        )
        
    return {
            "access_token": token,  
            "token_type": "bearer"
    }
        
    
@router.post("/login", response_model=LoginResponse)
async def login(
    params: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    user, token = await authenticate_user(
        auth_id=params.auth_id,
        auth_type=params.auth_type,
        db=db,
        redis=redis,
        credential=params.credential
    )
    
    return LoginResponse(
        access_token=token,
        user=user
    )
    
@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[DBUser, Depends(get_current_user)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    await logout_user(token, redis)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)  
async def read_users_me(current_user: Annotated[DBUser, Depends(get_current_user)]):
    return current_user