from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.core.exceptions import APIError
from app.core.handlers import api_error_handler

print(settings.DATABASE_URL)
print(settings.REDIS_URL)

app = FastAPI(
    title="Moment",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.add_exception_handler(APIError, api_error_handler)