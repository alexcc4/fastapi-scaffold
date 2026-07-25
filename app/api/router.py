from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.auth import router as auth_router


class PingResponse(BaseModel):
    status: Literal["ok"]


api_router = APIRouter()
api_router.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["auth"],
)


@api_router.get(
    "/ping",
    response_model=PingResponse,
    summary="Application liveness probe",
    tags=["system"],
)
async def ping() -> PingResponse:
    return PingResponse(status="ok")
