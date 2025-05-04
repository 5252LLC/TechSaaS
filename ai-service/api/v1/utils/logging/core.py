"""
Core Logging Module for TechSaaS

This module provides the core functionality for the TechSaaS logging system,
including configuration, setup, and utility functions.
"""

import os
import sys
import logging
import logging.config
import logging.handlers
import json
import threading
import datetime
import enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Thread-local storage for request context
thread_local = threading.local()


class LoggingLevel(enum.Enum):
    """Enum for logging levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def setup_logging(
    app_name: str = "techsaas",
    level: Union[int, str, LoggingLevel] = LoggingLevel.INFO,
    log_dir: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 30,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = True,
    enable_syslog: bool = False,
    syslog_address: Optional[tuple] = None,
    enable_db: bool = False,
) -> Dict[str, Any]:
    """
    Setup logging configuration for the TechSaaS platform.
    
    Args:
        app_name: Name of the application
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files, defaults to ./logs
        max_file_size: Maximum size in bytes for each log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable logging to console
        enable_file: Enable logging to file
        enable_json: Enable logging in JSON format
        enable_syslog: Enable logging to syslog
        syslog_address: Address for syslog, e.g., ('localhost', 514)
        enable_db: Enable logging to database
        
    Returns:
        Dict containing the logging configuration
    """
    # Convert LoggingLevel enum to int if necessary
    if isinstance(level, LoggingLevel):
        level = level.value
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Set up log directory
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%dT%H:%M:%S%z',
            },
            'json': {
                '()': 'ai_service.api.v1.utils.logging.formatters.JsonFormatter',
                'app_name': app_name,
            },
        },
        'handlers': {},
        'loggers': {
            '': {  # Root logger
                'handlers': [],
                'level': level,
                'propagate': True,
            },
            app_name: {
                'handlers': [],
                'level': level,
                'propagate': False,
            },
            'werkzeug': {
                'handlers': [],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    
    handlers = []
    
    # Console handler
    if enable_console:
        handlers.append('console')
        config['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'level': level,
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        }
    
    # File handlers
    if enable_file:
        # Standard log file
        handlers.append('file')
        log_file = os.path.join(log_dir, f'{app_name}.log')
        config['handlers']['file'] = {
            'class': 'ai_service.api.v1.utils.logging.handlers.RotatingFileHandlerWithCompression',
            'level': level,
            'formatter': 'standard',
            'filename': log_file,
            'maxBytes': max_file_size,
            'backupCount': backup_count,
            'encoding': 'utf8',
        }
        
        # Error log file (always enabled if file logging is on)
        handlers.append('error_file')
        error_log_file = os.path.join(log_dir, f'{app_name}_error.log')
        config['handlers']['error_file'] = {
            'class': 'ai_service.api.v1.utils.logging.handlers.RotatingFileHandlerWithCompression',
            'level': logging.ERROR,
            'formatter': 'standard',
            'filename': error_log_file,
            'maxBytes': max_file_size,
            'backupCount': backup_count,
            'encoding': 'utf8',
        }
        
        # JSON log file
        if enable_json:
            handlers.append('json_file')
            json_log_file = os.path.join(log_dir, f'{app_name}_json.log')
            config['handlers']['json_file'] = {
                'class': 'ai_service.api.v1.utils.logging.handlers.RotatingFileHandlerWithCompression',
                'level': level,
                'formatter': 'json',
                'filename': json_log_file,
                'maxBytes': max_file_size,
                'backupCount': backup_count,
                'encoding': 'utf8',
            }
    
    # Syslog handler
    if enable_syslog:
        handlers.append('syslog')
        if syslog_address is None:
            # Default to local syslog
            syslog_address = '/dev/log' if sys.platform.startswith('linux') else ('localhost', 514)
        
        config['handlers']['syslog'] = {
            'class': 'logging.handlers.SysLogHandler',
            'level': level,
            'formatter': 'standard',
            'address': syslog_address,
            'facility': 'local1',
        }
    
    # Database handler
    if enable_db:
        handlers.append('database')
        config['handlers']['database'] = {
            'class': 'ai_service.api.v1.utils.logging.handlers.DatabaseLogHandler',
            'level': level,
        }
    
    # Update handlers for loggers
    for logger_name in config['loggers']:
        config['loggers'][logger_name]['handlers'] = handlers
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    return config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_request_context() -> Dict[str, Any]:
    """
    Get the request context from thread local storage.
    
    Returns:
        Dictionary containing request context information
    """
    if not hasattr(thread_local, 'request_context'):
        thread_local.request_context = {}
    return thread_local.request_context


def set_request_context(context: Dict[str, Any]) -> None:
    """
    Set the request context in thread local storage.
    
    Args:
        context: Dictionary containing request context information
    """
    thread_local.request_context = context


def clear_request_context() -> None:
    """Clear the request context from thread local storage."""
    if hasattr(thread_local, 'request_context'):
        delattr(thread_local, 'request_context')


def set_context_value(key: str, value: Any) -> None:
    """
    Set a value in the request context.
    
    Args:
        key: Context key
        value: Context value
    """
    context = get_request_context()
    context[key] = value


def get_context_value(key: str, default: Any = None) -> Any:
    """
    Get a value from the request context.
    
    Args:
        key: Context key
        default: Default value if key is not found
        
    Returns:
        Value from the request context
    """
    context = get_request_context()
    return context.get(key, default)
