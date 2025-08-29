from pydantic import BaseModel


class EchoMessage(BaseModel):
    message: str


class EchoResponse(BaseModel):
    message: str
    user_id: int