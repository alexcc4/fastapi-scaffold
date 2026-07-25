from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app.api import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.mysql import close_database
from app.db.redis import close_redis
from app.middlewares import RequestObservabilityMiddleware


class ScaffoldFastAPI(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        return RequestObservabilityMiddleware(
            super().build_middleware_stack()
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis()
    await close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    app = ScaffoldFastAPI(
        title="FastAPI Scaffold",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Server-Timing"],
    )
    app.include_router(api_router)
    return app


app = create_app()
