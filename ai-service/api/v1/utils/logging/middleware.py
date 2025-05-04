"""
Logging Middleware for TechSaaS

This module provides middleware components that capture request information
and store it in the logging context for comprehensive request logging.
"""

import time
import logging
from typing import Dict, Any, Callable, Optional
from flask import Flask, request, g, Response
from werkzeug.wrappers import Request, Response as WerkzeugResponse

from api.v1.utils.logging.core import (
    get_logger,
    set_request_context,
    clear_request_context,
    get_context_value,
    set_context_value,
)
from api.v1.utils.logging.masking import mask_pii


logger = get_logger("techsaas.middleware")


class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests and responses.
    
    This middleware captures information about incoming requests and outgoing
    responses, including:
    - HTTP method
    - URL path
    - Status code
    - Response time
    - User ID (if authenticated)
    - IP address
    - User agent
    - Referrer
    
    It also handles PII masking to ensure sensitive information isn't logged.
    """
    
    def __init__(
        self,
        app: Flask,
        log_request_headers: bool = True,
        log_request_body: bool = False,
        log_response_headers: bool = False,
        log_response_body: bool = False,
        sensitive_headers: Optional[list] = None,
        max_body_length: int = 10000,
    ):
        """
        Initialize the request logging middleware.
        
        Args:
            app: Flask application
            log_request_headers: Whether to log request headers
            log_request_body: Whether to log request body
            log_response_headers: Whether to log response headers
            log_response_body: Whether to log response body
            sensitive_headers: List of headers considered sensitive
            max_body_length: Maximum length to log for request/response bodies
        """
        self.app = app
        self.log_request_headers = log_request_headers
        self.log_request_body = log_request_body
        self.log_response_headers = log_response_headers
        self.log_response_body = log_response_body
        self.max_body_length = max_body_length
        
        # Default sensitive headers
        self.sensitive_headers = sensitive_headers or [
            'authorization',
            'x-api-key',
            'cookie',
            'password',
            'token',
            'session',
            'api-key',
            'access-token',
            'refresh-token',
            'jwt',
        ]
        
        # Register middleware with Flask app
        self._register_middleware()
    
    def _register_middleware(self) -> None:
        """Register middleware with Flask app."""
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)
    
    def _before_request(self) -> None:
        """Process request before it is handled by the view."""
        # Store request start time
        g.request_start_time = time.time()
        
        # Collect request context information
        context = {
            'ip': request.remote_addr,
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'user_agent': request.user_agent.string if request.user_agent else None,
            'referrer': request.referrer,
            'request_id': request.headers.get('X-Request-ID', ''),
            'correlation_id': request.headers.get('X-Correlation-ID', ''),
        }
        
        # Get authenticated user ID if available
        user_id = None
        if hasattr(g, 'user') and g.user:
            user_id = getattr(g.user, 'id', None)
        elif hasattr(g, 'user_id'):
            user_id = g.user_id
        
        if user_id:
            context['user_id'] = user_id
        
        # Add request headers if enabled
        if self.log_request_headers:
            headers = {}
            for key, value in request.headers.items():
                # Mask sensitive headers
                if key.lower() in self.sensitive_headers:
                    headers[key] = '********'
                else:
                    headers[key] = value
            context['headers'] = headers
        
        # Add request body if enabled
        if self.log_request_body and request.is_json:
            try:
                # Use a copy of the JSON to avoid consuming the request stream
                json_data = request.get_json(silent=True, cache=True)
                if json_data:
                    # Mask PII in request body
                    masked_data = mask_pii(json_data)
                    body_str = str(masked_data)
                    if len(body_str) > self.max_body_length:
                        body_str = body_str[:self.max_body_length] + '... [truncated]'
                    context['body'] = body_str
            except Exception as e:
                logger.warning(f"Error processing request body: {e}")
        
        # Set request context for logging
        set_request_context(context)
        
        # Log the incoming request
        logger.info(f"Request started: {request.method} {request.path}")
    
    def _after_request(self, response: Response) -> Response:
        """Process response before it is returned to the client."""
        # Calculate response time
        if hasattr(g, 'request_start_time'):
            response_time = (time.time() - g.request_start_time) * 1000  # Convert to milliseconds
            set_context_value('response_time', response_time)
        else:
            response_time = 0
            
        # Set response status
        set_context_value('status', response.status_code)
        
        # Add response headers if enabled
        if self.log_response_headers:
            headers = {}
            for key, value in response.headers.items():
                # Mask sensitive headers
                if key.lower() in self.sensitive_headers:
                    headers[key] = '********'
                else:
                    headers[key] = value
            set_context_value('response_headers', headers)
        
        # Add response body if enabled
        if self.log_response_body:
            try:
                if response.is_json:
                    # Get JSON data
                    json_data = response.get_json(silent=True)
                    if json_data:
                        # Mask PII in response body
                        masked_data = mask_pii(json_data)
                        body_str = str(masked_data)
                        if len(body_str) > self.max_body_length:
                            body_str = body_str[:self.max_body_length] + '... [truncated]'
                        set_context_value('response_body', body_str)
            except Exception as e:
                logger.warning(f"Error processing response body: {e}")
        
        # Log the outgoing response
        logger.info(
            f"Request completed: {request.method} {request.path} - "
            f"Status: {response.status_code} - {response_time:.2f}ms"
        )
        
        return response
    
    def _teardown_request(self, exception: Optional[Exception]) -> None:
        """Clean up after the request is processed."""
        # Log any uncaught exceptions
        if exception:
            logger.error(f"Uncaught exception: {exception}", exc_info=exception)
        
        # Clear request context
        clear_request_context()


def init_app(app: Flask) -> None:
    """Initialize request logging middleware for the Flask app."""
    # Configure which sensitive information to log based on environment
    log_request_body = app.config.get('LOG_REQUEST_BODY', False)
    log_response_body = app.config.get('LOG_RESPONSE_BODY', False)
    
    # In production, be more restrictive with what we log
    if app.config.get('ENV') == 'production':
        log_request_body = False
        log_response_body = False
    
    # Set up the middleware
    RequestLoggingMiddleware(
        app=app,
        log_request_headers=app.config.get('LOG_REQUEST_HEADERS', True),
        log_request_body=log_request_body,
        log_response_headers=app.config.get('LOG_RESPONSE_HEADERS', False),
        log_response_body=log_response_body,
        max_body_length=app.config.get('MAX_LOG_BODY_LENGTH', 10000),
    )
