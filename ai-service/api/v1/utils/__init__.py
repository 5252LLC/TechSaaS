"""
Utility functions and helpers for the TechSaaS AI Service
"""

import os
import time
import logging
import uuid
from functools import wraps
from flask import request, jsonify, current_app

logger = logging.getLogger(__name__)

def generate_request_id():
    """Generate a unique request ID"""
    return str(uuid.uuid4())

def log_request(f):
    """Decorator to log API requests with timing"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Generate request ID
        request_id = generate_request_id()
        
        # Add request ID to request object
        request.request_id = request_id
        
        # Log request details
        logger.info(f"Request {request_id} started: {request.method} {request.path}")
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = f(*args, **kwargs)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log response details
        logger.info(f"Request {request_id} completed in {duration:.3f}s with status {response.status_code}")
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response
    return decorated

def validate_api_key():
    """
    Validates the API key from the request headers
    Returns True if valid, False otherwise
    """
    # Get API key from headers
    api_key = request.headers.get('Authorization')
    
    # If no Authorization header or wrong format, check for api_key query parameter
    if not api_key or not api_key.startswith('Bearer '):
        api_key = request.args.get('api_key')
        if not api_key:
            return False
    else:
        # Extract the key from "Bearer <api_key>"
        api_key = api_key.split(' ', 1)[1]
    
    # In a real implementation, validate against stored keys
    # For now, check against environment variable (dummy implementation)
    valid_key = os.getenv('API_KEY')
    
    # If we're in development and no key is set, allow access
    if current_app.config['ENV'] == 'development' and not valid_key:
        return True
        
    return api_key == valid_key

def require_api_key(f):
    """Decorator to require a valid API key for access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not validate_api_key():
            return jsonify({
                "error": "Unauthorized",
                "message": "Valid API key required"
            }), 401
        return f(*args, **kwargs)
    return decorated
