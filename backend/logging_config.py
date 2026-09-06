"""
Centralized structured logging configuration for PMS.
Injects unique Request IDs across all log messages using contextvars
to enable full-path distributed tracing for incoming HTTP requests.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Thread-safe context variable holding the active HTTP Request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("pms")

def get_request_id() -> str:
    """Returns the current request ID from context, or '-' if outside a request context."""
    return request_id_var.get()

def set_request_id(req_id: str) -> None:
    """Sets the active request ID in context."""
    request_id_var.set(req_id)

class RequestIdFilter(logging.Filter):
    """Logging filter that injects the current request ID into every LogRecord."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures root and PMS loggers with standard format:
    %(asctime)s [%(levelname)s] [req_id=%(request_id)s] %(name)s: %(message)s
    """
    log_format = "%(asctime)s [%(levelname)s] [req_id=%(request_id)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)
    
    req_filter = RequestIdFilter()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing stream handlers to prevent duplicate output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(req_filter)
    
    root_logger.addHandler(console_handler)
    
    # Ensure specific PMS loggers propagate through root
    for logger_name in ["pms.api", "pms.database", "pms.predictor", "pms.drift", "pms.scheduler", "pms.canary"]:
        sub_logger = logging.getLogger(logger_name)
        sub_logger.setLevel(level)
        sub_logger.propagate = True

# Automatically configure on module import
setup_logging()
