from fastapi import APIRouter

from app.api.v1.debug import router as debug_router
from app.api.v1.auth import router as auth_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(debug_router, prefix='/debug')
api_router.include_router(auth_router, prefix='/auth')
