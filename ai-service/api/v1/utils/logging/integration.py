"""
Logging System Integration for TechSaaS

This module provides integration functions to connect the logging system 
with the main Flask application and other components of TechSaaS.
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import Flask, current_app, request, g
import flask.cli

from api.v1.utils.logging.core import (
    setup_logging,
    get_logger,
    LoggingLevel,
)
from api.v1.utils.logging.middleware import (
    RequestLoggingMiddleware,
)


def configure_app_logging(app: Flask) -> None:
    """
    Configure logging for a Flask application.
    
    This function sets up the logging system for a Flask app, configuring
    handlers, middleware, and other components based on the app configuration.
    
    Args:
        app: Flask application to configure
    """
    # Disable Flask's default logging
    # This prevents duplicate logs from Flask's built-in logger
    flask.cli.show_server_banner = lambda *args, **kwargs: None
    
    # Get logging configuration from app config
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_dir = app.config.get('LOG_DIR', os.path.join(app.instance_path, 'logs'))
    app_name = app.config.get('APP_NAME', 'techsaas')
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Get more logging options from app config
    enable_file = app.config.get('LOG_TO_FILE', True)
    enable_json = app.config.get('LOG_JSON_FORMAT', True)
    enable_syslog = app.config.get('LOG_TO_SYSLOG', False)
    enable_db = app.config.get('LOG_TO_DATABASE', False)
    max_file_size = app.config.get('LOG_MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB
    backup_count = app.config.get('LOG_BACKUP_COUNT', 30)
    
    # Set up the logger
    setup_logging(
        app_name=app_name,
        level=log_level,
        log_dir=log_dir,
        max_file_size=max_file_size,
        backup_count=backup_count,
        enable_file=enable_file,
        enable_json=enable_json,
        enable_syslog=enable_syslog,
        enable_db=enable_db,
    )
    
    # Set up request logging middleware if enabled
    if app.config.get('ENABLE_REQUEST_LOGGING', True):
        # Create middleware
        middleware = RequestLoggingMiddleware(
            app=app,
            log_request_headers=app.config.get('LOG_REQUEST_HEADERS', True),
            log_request_body=app.config.get('LOG_REQUEST_BODY', False),
            log_response_headers=app.config.get('LOG_RESPONSE_HEADERS', False),
            log_response_body=app.config.get('LOG_RESPONSE_BODY', False),
            max_body_length=app.config.get('MAX_LOG_BODY_LENGTH', 10000),
        )
    
    # Set up log rotation if enabled
    if app.config.get('ENABLE_LOG_ROTATION', True):
        # This is handled by our RotatingFileHandlerWithCompression
        pass
    
    # Register logger in app context for easy access
    app.logger = get_logger(app_name)
    
    # Log startup message
    app.logger.info(f"Logging configured for {app_name} application")


def get_app_logger() -> logging.Logger:
    """
    Get the application logger from the current Flask app.
    
    This function provides easy access to the application logger in views
    and other components that have access to the Flask application context.
    
    Returns:
        Application logger
    """
    try:
        return current_app.logger
    except RuntimeError:
        # Not in application context, return a default logger
        return get_logger('techsaas')


def log_audit_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> None:
    """
    Log an audit event for security and compliance purposes.
    
    This function creates a standardized audit log entry that can be used 
    for security monitoring, compliance reporting, and forensic analysis.
    
    Args:
        event_type: Type of audit event (e.g., 'login', 'data_access')
        user_id: ID of the user who performed the action
        details: Additional details about the action
        success: Whether the action was successful
    """
    logger = get_app_logger()
    
    # Get user ID from request context if not provided
    if user_id is None and hasattr(g, 'user'):
        user_id = getattr(g.user, 'id', None)
    
    # Get request information if available
    request_info = {}
    if request:
        request_info = {
            'ip': request.remote_addr,
            'method': request.method,
            'path': request.path,
            'user_agent': str(request.user_agent) if request.user_agent else None,
        }
    
    # Create audit log entry
    audit_data = {
        'event_type': event_type,
        'user_id': user_id,
        'success': success,
        'request': request_info,
    }
    
    # Add details if provided
    if details:
        audit_data['details'] = details
    
    # Log at appropriate level based on success
    if success:
        logger.info(f"AUDIT: {event_type}", extra={'audit': audit_data})
    else:
        logger.warning(f"AUDIT: {event_type} (failed)", extra={'audit': audit_data})


def init_app(app: Flask) -> None:
    """
    Initialize logging for a Flask application.
    
    This function should be called during application setup to configure
    the logging system with the Flask app.
    
    Args:
        app: Flask application to initialize
    """
    configure_app_logging(app)
