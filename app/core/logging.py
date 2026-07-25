import logging
import sys


LOG_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"


def setup_logging(level: str = "INFO") -> None:
    app_logger = logging.getLogger("app")
    configured_level = level.upper()
    app_logger.setLevel(
        configured_level
        if configured_level in logging.getLevelNamesMapping()
        else logging.INFO
    )
    if any(getattr(handler, "_app_handler", False) for handler in app_logger.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler._app_handler = True  # type: ignore[attr-defined]

    app_logger.addHandler(handler)
    app_logger.propagate = False
