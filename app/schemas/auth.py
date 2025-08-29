from typing import Optional

from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    auth_id: str
    auth_type: int
    credential: Optional[str] = None
    auth_data: Optional[dict] = None


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse
