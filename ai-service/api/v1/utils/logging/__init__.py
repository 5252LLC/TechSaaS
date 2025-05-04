"""
Centralized Logging System for TechSaaS

This package provides a comprehensive logging framework for tracking API requests,
authentication attempts, and security events across the TechSaaS platform.
"""

from api.v1.utils.logging.core import (
    setup_logging,
    get_logger,
    LoggingLevel,
)
from api.v1.utils.logging.formatters import RequestFormatter
from api.v1.utils.logging.middleware import RequestLoggingMiddleware
from api.v1.utils.logging.handlers import (
    DatabaseLogHandler,
    RotatingFileHandlerWithCompression,
)
from api.v1.utils.logging.masking import mask_pii

__all__ = [
    'setup_logging',
    'get_logger',
    'LoggingLevel',
    'RequestFormatter',
    'RequestLoggingMiddleware',
    'DatabaseLogHandler',
    'RotatingFileHandlerWithCompression',
    'mask_pii',
]
