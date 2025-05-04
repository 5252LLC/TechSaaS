"""
Log Formatters for TechSaaS

This module provides custom log formatters that structure log data in various formats,
including JSON and specialized request formatting.
"""

import json
import logging
import datetime
import time
import socket
import traceback
from typing import Dict, Any, Optional

from api.v1.utils.logging.core import get_request_context
from api.v1.utils.logging.masking import mask_pii


class JsonFormatter(logging.Formatter):
    """
    Format log records as JSON objects.
    
    This formatter ensures that log records are structured in a consistent JSON format
    for easy parsing and analysis by log management systems.
    """
    
    def __init__(self, app_name: str = "techsaas", include_stack_info: bool = True):
        """
        Initialize the JSON formatter.
        
        Args:
            app_name: Name of the application
            include_stack_info: Whether to include stack traces for exceptions
        """
        super().__init__()
        self.app_name = app_name
        self.include_stack_info = include_stack_info
        self.hostname = socket.gethostname()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.
        
        Args:
            record: LogRecord to format
            
        Returns:
            JSON string representation of the log record
        """
        # Get the basic log data
        log_data = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "app": self.app_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "hostname": self.hostname,
        }
        
        # Add exception info if available
        if record.exc_info and self.include_stack_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        # Add request context if available
        request_context = get_request_context()
        if request_context:
            # Mask PII in request context
            masked_context = mask_pii(request_context)
            log_data["request"] = masked_context
        
        # Add extra attributes
        if hasattr(record, "extras") and record.extras:
            for key, value in record.extras.items():
                if key not in log_data:
                    log_data[key] = value
        
        return json.dumps(log_data)


class RequestFormatter(logging.Formatter):
    """
    A specialized formatter for HTTP request logs.
    
    This formatter includes request-specific information such as method, path, status code,
    and response time, making it ideal for API request logging.
    """
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """
        Initialize the request formatter.
        
        Args:
            fmt: Format string
            datefmt: Date format string
        """
        if fmt is None:
            fmt = '%(asctime)s [%(levelname)s] [%(ip)s] "%(method)s %(path)s" %(status)s %(response_time).2fms - %(message)s'
        if datefmt is None:
            datefmt = '%Y-%m-%dT%H:%M:%S%z'
        
        super().__init__(fmt=fmt, datefmt=datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with request information.
        
        Args:
            record: LogRecord to format
            
        Returns:
            Formatted log message
        """
        # Get request context
        request_context = get_request_context()
        
        # Add request context to record if available
        if request_context:
            for key, value in request_context.items():
                # Don't overwrite existing attributes
                if not hasattr(record, key):
                    setattr(record, key, value)
        
        # Set defaults for required attributes
        if not hasattr(record, 'ip'):
            setattr(record, 'ip', '-')
        if not hasattr(record, 'method'):
            setattr(record, 'method', '-')
        if not hasattr(record, 'path'):
            setattr(record, 'path', '-')
        if not hasattr(record, 'status'):
            setattr(record, 'status', '-')
        if not hasattr(record, 'response_time'):
            setattr(record, 'response_time', 0.0)
        
        return super().format(record)
