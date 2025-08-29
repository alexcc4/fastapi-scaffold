from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User as DBUser
from app.schemas.user import UserResponse


router = APIRouter()


@router.get("/me", response_model=UserResponse)  
async def read_users_me(current_user: Annotated[DBUser, Depends(get_current_user)]):
    return current_user
