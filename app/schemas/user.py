from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserResponse(BaseModel):
    id: int
    clerk_id: str
    email: str
    name: str
    status: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    }
