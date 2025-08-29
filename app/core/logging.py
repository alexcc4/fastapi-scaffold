import logging
import sys


def setup_logging(level=logging.INFO):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(handler)
    
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    
    return app_logger
