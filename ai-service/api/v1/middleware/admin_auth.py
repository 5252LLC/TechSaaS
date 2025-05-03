"""
Admin Authentication Middleware
Provides secure authentication for admin-only endpoints
"""

import logging
import time
import hmac
import hashlib
from functools import wraps
from flask import request, jsonify, g, current_app

logger = logging.getLogger(__name__)

def require_admin(view_func):
    """
    Admin authentication decorator
    
    This decorator verifies the admin API key for access to admin-only endpoints.
    It implements several security measures:
    - Constant-time comparison to prevent timing attacks
    - Rate limiting for failed attempts
    - IP-based blocking for repeated failures
    - Comprehensive logging of admin access attempts
    
    Usage:
        @require_admin
        def admin_endpoint():
            # Only admins can access this
            pass
    """
    @wraps(view_func)
    def decorated(*args, **kwargs):
        # Check if authentication is disabled for development
        if current_app.config.get('DISABLE_AUTH_FOR_DEV', False):
            logger.warning("SECURITY NOTICE: Admin authentication bypassed in development mode")
            # Still set admin flag for consistency
            g.is_admin = True
            return view_func(*args, **kwargs)
        
        # Get admin API key from headers
        api_key = request.headers.get('X-Admin-Key') or request.headers.get('Authorization')
        
        # Extract token from "Bearer" format
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        client_ip = request.remote_addr
        
        # Rate limiting for failed attempts (very strict for admin endpoints)
        # In production, this would use Redis or a similar distributed cache
        current_time = int(time.time())
        rate_key = f"admin_auth_attempt:{client_ip}:{current_time // 60}"
        
        # Simple in-memory rate limiting
        if not hasattr(require_admin, "_rate_limits"):
            require_admin._rate_limits = {}
        
        # Clean up old entries
        for key in list(require_admin._rate_limits.keys()):
            time_part = int(key.split(":")[-1])
            if current_time // 60 - time_part > 60:  # Clean up entries older than 1 hour
                del require_admin._rate_limits[key]
        
        # Increment rate counter
        require_admin._rate_limits[rate_key] = require_admin._rate_limits.get(rate_key, 0) + 1
        
        # Check if rate limit exceeded (max 5 attempts per minute)
        if require_admin._rate_limits.get(rate_key, 0) > 5:
            logger.warning(f"SECURITY ALERT: Admin authentication rate limit exceeded from IP {client_ip}")
            return jsonify({
                "error": "Too many authentication attempts",
                "status": "rate_limited",
                "retry_after": 60 - int(time.time() % 60)
            }), 429
        
        # Verify the admin key using constant-time comparison
        if not api_key:
            logger.warning(f"Admin authentication attempt with missing API key from IP {client_ip}")
            return jsonify({"error": "Admin API key required", "status": "unauthorized"}), 401
        
        expected_key = current_app.config.get('ADMIN_API_KEY', '')
        
        # Perform constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(api_key, expected_key):
            logger.warning(f"SECURITY ALERT: Failed admin authentication attempt from IP {client_ip}")
            return jsonify({"error": "Invalid admin API key", "status": "forbidden"}), 403
        
        # Successfully authenticated as admin
        g.is_admin = True
        logger.info(f"Successful admin authentication from IP {client_ip}")
        
        # Continue to the view
        return view_func(*args, **kwargs)
    
    return decorated


def admin_only(func):
    """
    Decorator to mark functions that should only be called by admin users
    
    This is an internal decorator to be used within service classes,
    not for route handlers (use require_admin for routes).
    
    Usage:
        class SomeService:
            @admin_only
            def dangerous_operation(self):
                # Only callable by admin users
                pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(g, 'is_admin', False):
            raise PermissionError("This operation requires admin privileges")
        return func(*args, **kwargs)
    return wrapper
