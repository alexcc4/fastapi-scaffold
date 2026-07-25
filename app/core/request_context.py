from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestContext:
    request_id: str
    method: str
    path: str
    session_fingerprint: str | None = None


request_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context",
    default=None,
)


def get_request_context() -> RequestContext | None:
    return request_context.get()
