from fastapi import APIRouter, Depends

from app.core.deps import get_current_user


router = APIRouter()


@router.get("/me", response_model=dict)  # 添加响应模型
async def read_users_me(current_user_id: str = Depends(get_current_user)):
    return {"user_id": current_user_id}
