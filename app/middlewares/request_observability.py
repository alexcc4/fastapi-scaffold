import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import RequestContext, request_context


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
ACCESS_LOGGER = logging.getLogger("app.access")


def normalize_request_id(value: str | None) -> str:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


class RequestObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope["path"]
        request_id = normalize_request_id(
            Headers(scope=scope).get("x-request-id")
        )
        context = RequestContext(
            request_id=request_id,
            method=method,
            path=path,
        )
        context_token = request_context.set(context)
        started_at = perf_counter()
        status_code = 500

        async def send_with_observability(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = (perf_counter() - started_at) * 1000
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
            await send(message)

        try:
            await self.app(scope, receive, send_with_observability)
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            if path != "/ping":
                session_field = (
                    f" session_fp={context.session_fingerprint}"
                    if context.session_fingerprint is not None
                    else ""
                )
                ACCESS_LOGGER.info(
                    "request_completed request_id=%s method=%s path=%r "
                    "status=%d duration_ms=%.2f%s",
                    request_id,
                    method,
                    path,
                    status_code,
                    duration_ms,
                    session_field,
                )
            request_context.reset(context_token)
