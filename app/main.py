import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging
from app.core.config import settings
from app.middleware.timing import TimingMiddleware
from app.api.v1 import api_router
from app.db.session import close_db_engine
from app.db.redis import pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Application starting...")
    
    yield
    
    logger.info("🛑 Application closing...")
    await close_db_engine()
    if pool:
        await pool.aclose()
    logger.info("✅ Resources cleaned up")


logger = setup_logging(logging.DEBUG if settings.DEBUG else logging.INFO)

app = FastAPI(
    title="FastAPI Backend Template",
    version="0.1.0",
    openapi_url=f"/openapi.json",
    lifespan=lifespan,  
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TimingMiddleware)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)