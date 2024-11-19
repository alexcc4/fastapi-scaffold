from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import APIError


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """处理所有 API 错误"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    ) 