import time
import logging
import sys
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.access")
if not logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.INFO)


class TimingMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response_time_ms = round(process_time * 1000, 2)
        
        content_length = response.headers.get("Content-Length", "-")
        
        logger.info(
            f"{datetime.now()} {request.method} {request.url} {response.status_code} {response_time_ms}ms {content_length}"
        )
        
        response.headers["X-Process-Time"] = str(response_time_ms)
        
        return response

