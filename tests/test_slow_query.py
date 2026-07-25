from unittest.mock import patch

from sqlalchemy import create_engine

from app.core.request_context import RequestContext, request_context
from app.db.slow_query import install_slow_query_logging


def _logged_message(log) -> str:
    return log.call_args.args[0] % log.call_args.args[1:]


def test_slow_query_never_logs_sql_text_or_parameters() -> None:
    engine = create_engine("sqlite://")
    install_slow_query_logging(
        engine,
        threshold_seconds=0,
    )
    context_token = request_context.set(
        RequestContext(
            request_id="request-123",
            method="GET",
            path="/items",
        )
    )
    try:
        with patch("app.db.slow_query.SLOW_QUERY_LOGGER.warning") as log:
            with engine.connect() as connection:
                connection.exec_driver_sql(
                    "SELECT 'top-secret-literal', ?",
                    ("top-secret-parameter",),
                )
    finally:
        request_context.reset(context_token)
        engine.dispose()

    log.assert_called_once()
    logged = _logged_message(log)
    assert "operation=SELECT" in logged
    assert "request_id=request-123" in logged
    assert "top-secret-literal" not in logged
    assert "top-secret-parameter" not in logged


def test_slow_query_logs_stable_statement_metadata() -> None:
    engine = create_engine("sqlite://")
    install_slow_query_logging(
        engine,
        threshold_seconds=0,
    )
    with patch("app.db.slow_query.SLOW_QUERY_LOGGER.warning") as log:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    engine.dispose()

    log.assert_called_once()
    logged = _logged_message(log)
    assert "sql=" not in logged
    assert "sql_hash=" in logged
    assert "sql_length=8" in logged


def test_slow_query_below_threshold_is_not_logged() -> None:
    engine = create_engine("sqlite://")
    install_slow_query_logging(
        engine,
        threshold_seconds=0.1,
    )
    with (
        patch("app.db.slow_query.perf_counter", side_effect=[0.0, 0.05]),
        patch("app.db.slow_query.SLOW_QUERY_LOGGER.warning") as log,
    ):
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    engine.dispose()

    log.assert_not_called()


def test_slow_query_at_threshold_is_logged() -> None:
    engine = create_engine("sqlite://")
    install_slow_query_logging(
        engine,
        threshold_seconds=0.1,
    )
    with (
        patch("app.db.slow_query.perf_counter", side_effect=[0.0, 0.1]),
        patch("app.db.slow_query.SLOW_QUERY_LOGGER.warning") as log,
    ):
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    engine.dispose()

    log.assert_called_once()
    logged = _logged_message(log)
    assert "duration_ms=100.00" in logged
    assert "threshold_ms=100.00" in logged
