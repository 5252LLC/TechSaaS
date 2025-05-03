"""
Security Middleware Integration Module
Centralizes all security-related middleware and provides
a unified integration point for the Flask application.
"""

import logging
from functools import wraps
from flask import request, g, jsonify
import jwt
from datetime import datetime

from api.v1.utils.config import JWT_SECRET_KEY, JWT_ALGORITHM
from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.middleware.authorization import init_authorization_middleware

# Setup logger
logger = logging.getLogger(__name__)

def init_security_middleware(app):
    """
    Initialize all security middleware for the Flask application
    
    Args:
        app: Flask application instance
    """
    # Register JWT authentication middleware
    @app.before_request
    def authenticate_jwt():
        """Extract and validate JWT token from request"""
        # Skip authentication for public endpoints
        public_endpoints = [
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/auth/refresh',
            '/static/',
            '/favicon.ico'
        ]
        
        # Check if the current path should skip authentication
        for endpoint in public_endpoints:
            if request.path.startswith(endpoint):
                return None
        
        start_time = datetime.now().timestamp()
        
        # Get token from headers
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            # No token provided for protected endpoint
            logger.info(f"Missing or invalid Authorization header for {request.path}")
            return None  # Allow the request to continue - protected endpoints will check g.user
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        try:
            # Decode and validate token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Set user data in Flask g object for access in views
            g.user = payload
            
            # Log successful authentication
            logger.debug(f"Authenticated user {payload.get('sub')} with role {payload.get('role')}")
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token used for {request.path}")
            response = ResponseFormatter.error_response(
                message="Token has expired",
                error_type="token_expired",
                error="Expired JWT token",
                status_code=401,
                start_time=start_time
            )
            return response
            
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token used for {request.path}")
            response = ResponseFormatter.error_response(
                message="Invalid token",
                error_type="token_invalid",
                error="Invalid JWT token",
                status_code=401,
                start_time=start_time
            )
            return response
        
        return None
    
    # Initialize authorization middleware
    init_authorization_middleware(app)
    
    # Register security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'"
        
        # Prevent caching of sensitive API responses
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    # Register request logging for sensitive operations
    @app.before_request
    def log_sensitive_operations():
        """Log sensitive operations for audit purposes"""
        sensitive_paths = [
            '/api/v1/admin',
            '/api/v1/user',
            '/api/v1/billing',
            '/api/v1/subscription'
        ]
        
        sensitive_operations = [
            'DELETE',
            'PUT',
            'PATCH'
        ]
        
        # Check if this is a sensitive operation
        is_sensitive_path = any(request.path.startswith(path) for path in sensitive_paths)
        is_sensitive_method = request.method in sensitive_operations
        
        if is_sensitive_path or is_sensitive_method:
            # Get user info if authenticated
            user_id = getattr(g, 'user', {}).get('sub', 'anonymous')
            user_role = getattr(g, 'user', {}).get('role', 'anonymous')
            
            # Log the operation
            logger.info(f"Sensitive Operation: user={user_id}, role={user_role}, method={request.method}, path={request.path}, ip={request.remote_addr}")
    
    # Return success message
    logger.info("Security middleware initialized successfully")
    return True

def jwt_required(f):
    """
    Decorator to ensure a valid JWT token is present
    
    Usage:
        @jwt_required
        def protected_route():
            # Only authenticated users can access this
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = datetime.now().timestamp()
        
        # Check if user is authenticated (set by before_request handler)
        if not hasattr(g, 'user'):
            response = ResponseFormatter.error_response(
                message="Authentication required",
                error_type="authentication_error",
                error="No valid authentication token provided",
                status_code=401,
                start_time=start_time
            )
            return response
        
        # User is authenticated, continue
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """
    Decorator to ensure an authenticated user has admin role
    
    Usage:
        @admin_required
        def admin_route():
            # Only admin users can access this
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = datetime.now().timestamp()
        
        # Check if user is authenticated
        if not hasattr(g, 'user'):
            response = ResponseFormatter.error_response(
                message="Authentication required",
                error_type="authentication_error",
                error="No valid authentication token provided",
                status_code=401,
                start_time=start_time
            )
            return response
        
        # Check if user is an admin
        if g.user.get('role') not in ['admin', 'superadmin']:
            response = ResponseFormatter.error_response(
                message="Admin access required",
                error_type="authorization_error",
                error="User does not have admin privileges",
                status_code=403,
                start_time=start_time
            )
            return response
        
        # User is an admin, continue
        return f(*args, **kwargs)
    
    return decorated
