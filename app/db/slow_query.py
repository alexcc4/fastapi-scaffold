import hashlib
import logging
import re
from time import perf_counter
from typing import Any
from weakref import WeakSet

from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine

from app.core.request_context import get_request_context


SLOW_QUERY_LOGGER = logging.getLogger("app.db.slow_query")
TIMER_STACK_KEY = "_slow_query_started_at"
WHITESPACE_PATTERN = re.compile(r"\s+")
INSTALLED_ENGINES: WeakSet[Engine] = WeakSet()


def normalize_sql(statement: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", statement).strip()


def sql_operation(statement: str) -> str:
    normalized = normalize_sql(statement)
    if not normalized:
        return "UNKNOWN"
    return normalized.split(" ", 1)[0].upper()


def install_slow_query_logging(
    engine: Engine,
    *,
    threshold_seconds: float,
) -> None:
    if engine in INSTALLED_ENGINES:
        return

    def before_cursor_execute(
        connection: Connection,
        _cursor: Any,
        _statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        connection.info.setdefault(TIMER_STACK_KEY, []).append(perf_counter())

    def after_cursor_execute(
        connection: Connection,
        cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        executemany: bool,
    ) -> None:
        stack = connection.info.get(TIMER_STACK_KEY, [])
        if not stack:
            return

        duration_seconds = perf_counter() - stack.pop()
        if duration_seconds < threshold_seconds:
            return

        normalized = normalize_sql(statement)
        sql_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        rowcount = getattr(cursor, "rowcount", -1)
        rowcount_field = rowcount if rowcount >= 0 else "-"
        context = get_request_context()
        context_fields = ""
        if context is not None:
            context_fields = (
                f" request_id={context.request_id}"
                f" method={context.method} path={context.path!r}"
            )
        SLOW_QUERY_LOGGER.warning(
            "slow_query duration_ms=%.2f threshold_ms=%.2f "
            "operation=%s sql_hash=%s sql_length=%d executemany=%s "
            "rowcount=%s%s",
            duration_seconds * 1000,
            threshold_seconds * 1000,
            sql_operation(normalized),
            sql_hash,
            len(normalized),
            str(executemany).lower(),
            rowcount_field,
            context_fields,
        )

    def handle_error(exception_context: Any) -> None:
        connection = exception_context.connection
        if connection is None:
            return
        stack = connection.info.get(TIMER_STACK_KEY, [])
        if stack:
            stack.pop()

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    event.listen(engine, "handle_error", handle_error)
    INSTALLED_ENGINES.add(engine)
