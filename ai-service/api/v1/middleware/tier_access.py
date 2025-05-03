"""
Tier Access Middleware
Enforces tier-based access controls and rate limiting for the API
"""

import time
import logging
from functools import wraps
from flask import request, jsonify, g, current_app
import threading

# Setup logger
logger = logging.getLogger(__name__)

# Thread-safe rate limit counters (in production, use Redis or similar)
class RateLimitStore:
    def __init__(self):
        self.counters = {}
        self.lock = threading.Lock()
    
    def increment(self, key, window_size=60):
        """Increment rate counter for key in the current time window"""
        current_window = int(time.time() / window_size)
        counter_key = f"{key}:{current_window}"
        
        with self.lock:
            if counter_key not in self.counters:
                # Clean up old entries
                for k in list(self.counters.keys()):
                    if not k.startswith(f"{key}:"):
                        continue
                    
                    window = int(k.split(':')[1])
                    if window < current_window:
                        del self.counters[k]
                        
                self.counters[counter_key] = 0
            
            self.counters[counter_key] += 1
            return self.counters[counter_key]
    
    def get_count(self, key, window_size=60):
        """Get current rate count for key in this time window"""
        current_window = int(time.time() / window_size)
        counter_key = f"{key}:{current_window}"
        
        with self.lock:
            return self.counters.get(counter_key, 0)

# Global rate limit store
rate_limit_store = RateLimitStore()

# API key validation & retrieval (in production, use a database)
def get_api_key_details(api_key):
    """
    Get API key details from the key value
    
    Args:
        api_key (str): The API key to validate
        
    Returns:
        dict: API key details or None if invalid
    """
    # This would normally query a database
    # For now, accept a test key and return mock data
    if api_key == "test_key" or api_key.startswith("ts_"):
        return {
            "valid": True,
            "user_id": "user-1234",
            "tier": "basic",  # basic, pro, enterprise
            "permissions": ["read", "write"],
            "rate_limit": 100,  # requests per minute
            "daily_quota": 10000
        }
    
    return None

def require_auth(view_func):
    """
    Authentication decorator that requires a valid API key
    
    This decorator checks for a valid API key in the request headers
    and adds the key details to the Flask g object for use in the view
    """
    @wraps(view_func)
    def decorated(*args, **kwargs):
        # Check if authentication is disabled for development
        if current_app.config.get('DISABLE_AUTH_FOR_DEV', False):
            # Use a default tier for development
            g.api_key = {
                "valid": True,
                "user_id": "dev-user",
                "tier": "enterprise",  # Give full access in development
                "permissions": ["read", "write", "admin"],
                "rate_limit": 1000,
                "daily_quota": 100000
            }
            return view_func(*args, **kwargs)
        
        # Get API key from headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        # Extract token from "Bearer" format
        if api_key and api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        if not api_key:
            return jsonify({"error": "API key is required", "status": "unauthorized"}), 401
        
        # Validate API key
        key_details = get_api_key_details(api_key)
        
        if not key_details or not key_details.get('valid'):
            return jsonify({"error": "Invalid API key", "status": "unauthorized"}), 401
        
        # Store API key details in Flask g
        g.api_key = key_details
        
        # Continue to the view
        return view_func(*args, **kwargs)
    
    return decorated

def require_tier(minimum_tier):
    """
    Decorator that requires a minimum subscription tier
    
    Args:
        minimum_tier (str): Minimum required tier (basic, pro, enterprise)
        
    Usage:
        @require_tier('pro')
        def premium_endpoint():
            # This will only run for pro or enterprise users
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated(*args, **kwargs):
            # Must be used after require_auth
            if not hasattr(g, 'api_key'):
                return jsonify({"error": "Authentication required", "status": "unauthorized"}), 401
            
            # Check tier hierarchy
            tiers = {
                "basic": 0,
                "pro": 1,
                "enterprise": 2
            }
            
            user_tier = g.api_key.get('tier', 'basic')
            
            if tiers.get(user_tier, 0) < tiers.get(minimum_tier, 0):
                return jsonify({
                    "error": f"This endpoint requires {minimum_tier} tier or higher",
                    "status": "forbidden",
                    "current_tier": user_tier,
                    "required_tier": minimum_tier,
                    "upgrade_url": "/api/v1/subscription/plans/upgrade"
                }), 403
            
            # Continue to the view
            return view_func(*args, **kwargs)
        
        return decorated
    
    return decorator

def enforce_rate_limit(view_func):
    """
    Decorator to enforce rate limits based on API key tier
    
    Must be used after require_auth to ensure g.api_key is available
    """
    @wraps(view_func)
    def decorated(*args, **kwargs):
        # Must be used after require_auth
        if not hasattr(g, 'api_key'):
            return jsonify({"error": "Authentication required", "status": "unauthorized"}), 401
        
        # Get rate limit for this tier
        user_id = g.api_key.get('user_id')
        rate_limit = g.api_key.get('rate_limit', 100)  # defaults to 100 req/min
        
        # Check rate limit
        current_count = rate_limit_store.increment(f"rate:{user_id}")
        
        # Set rate limit headers
        response = None
        
        if current_count > rate_limit:
            response = jsonify({
                "error": "Rate limit exceeded",
                "status": "too_many_requests",
                "limit": rate_limit,
                "current": current_count,
                "retry_after": 60 - int(time.time() % 60)  # Seconds until next window
            })
            response.status_code = 429
        else:
            # Continue to the view
            response = view_func(*args, **kwargs)
        
        # Add rate limit headers to response
        if hasattr(response, 'headers'):
            response.headers['X-RateLimit-Limit'] = str(rate_limit)
            response.headers['X-RateLimit-Remaining'] = str(max(0, rate_limit - current_count))
            response.headers['X-RateLimit-Reset'] = str(60 - int(time.time() % 60))
        
        return response
    
    return decorated

def track_usage(category, operation=None):
    """
    Decorator to track API usage for billing
    
    Args:
        category (str): Usage category (ai, multimodal)
        operation (str, optional): Specific operation being performed
        
    Usage:
        @track_usage('ai', 'analyze')
        def analyze_text():
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated(*args, **kwargs):
            start_time = time.time()
            
            # Call the view function
            response = view_func(*args, **kwargs)
            
            # Track usage after successful response (not for errors)
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                # Get user from API key
                user_id = getattr(g, 'api_key', {}).get('user_id', 'anonymous')
                tier = getattr(g, 'api_key', {}).get('tier', 'basic')
                
                # Calculate usage metrics
                duration_ms = int((time.time() - start_time) * 1000)
                
                # In production, this would record to a database
                logger.info(f"USAGE: user={user_id} tier={tier} category={category} "
                           f"operation={operation} duration_ms={duration_ms}")
                
                # Track additional metrics based on response data
                if hasattr(response, 'get_json'):
                    try:
                        data = response.get_json()
                        if isinstance(data, dict):
                            # Track tokens for AI completions
                            if category == 'ai' and operation == 'completion':
                                tokens = data.get('tokens_used', 0)
                                logger.info(f"USAGE_METRIC: user={user_id} metric=tokens value={tokens}")
                            
                            # Track processing units for multimodal
                            if category == 'multimodal':
                                units = 1  # Default to 1 unit per request
                                if operation == 'video':
                                    # Charge by video duration
                                    duration_sec = data.get('video_duration_seconds', 60)
                                    units = max(1, int(duration_sec / 60))
                                
                                logger.info(f"USAGE_METRIC: user={user_id} metric=units value={units}")
                    except:
                        pass
            
            return response
        
        return decorated
    
    return decorator
