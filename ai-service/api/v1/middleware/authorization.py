"""
Authorization Middleware
Implements comprehensive authorization, access control, and permission checking
for the TechSaaS API. Works with the JWT authentication system.
"""

import time
import logging
import json
from functools import wraps
from flask import request, jsonify, g, current_app, abort
from datetime import datetime

from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.utils.config import TIER_FEATURES

# Setup logger
logger = logging.getLogger(__name__)

# Define permission constants
class Permissions:
    # General permissions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    
    # Feature-specific permissions
    SCRAPE_BASIC = "scrape:basic"
    SCRAPE_ADVANCED = "scrape:advanced"
    VIDEO_EXTRACTION = "video:extract"
    PENTESTING = "pentesting"
    AI_BASIC = "ai:basic"
    AI_ADVANCED = "ai:advanced"
    EXPORT_DATA = "export:data"
    ADMIN_VIEW = "admin:view"
    ADMIN_EDIT = "admin:edit"
    API_ACCESS = "api:access"
    
    # Role-based permission groups
    BASIC_PERMISSIONS = {
        READ,
        SCRAPE_BASIC,
        AI_BASIC,
        EXPORT_DATA
    }
    
    PREMIUM_PERMISSIONS = {
        READ,
        WRITE,
        SCRAPE_BASIC,
        SCRAPE_ADVANCED,
        VIDEO_EXTRACTION,
        AI_BASIC,
        AI_ADVANCED,
        EXPORT_DATA,
        API_ACCESS
    }
    
    PROFESSIONAL_PERMISSIONS = {
        READ,
        WRITE,
        DELETE,
        SCRAPE_BASIC,
        SCRAPE_ADVANCED,
        VIDEO_EXTRACTION,
        PENTESTING,
        AI_BASIC,
        AI_ADVANCED,
        EXPORT_DATA,
        API_ACCESS
    }
    
    ADMIN_PERMISSIONS = {
        READ,
        WRITE,
        DELETE,
        SCRAPE_BASIC,
        SCRAPE_ADVANCED,
        VIDEO_EXTRACTION,
        PENTESTING,
        AI_BASIC,
        AI_ADVANCED,
        EXPORT_DATA,
        ADMIN_VIEW,
        ADMIN_EDIT,
        API_ACCESS
    }

# Map tiers to permission sets
TIER_PERMISSIONS = {
    'free': set(),  # Free tier has no permissions by default
    'basic': Permissions.BASIC_PERMISSIONS,
    'premium': Permissions.PREMIUM_PERMISSIONS,
    'professional': Permissions.PROFESSIONAL_PERMISSIONS,
    'enterprise': Permissions.PROFESSIONAL_PERMISSIONS.union({Permissions.ADMIN_VIEW})
}

# Map roles to permission sets
ROLE_PERMISSIONS = {
    'user': set(),  # User role has no additional permissions beyond their tier
    'premium': set(),  # Premium users get permissions from their tier
    'admin': Permissions.ADMIN_PERMISSIONS,
    'superadmin': Permissions.ADMIN_PERMISSIONS.union({Permissions.DELETE})
}

def get_user_permissions(user_data):
    """
    Get all permissions for a user based on their tier and role
    
    Args:
        user_data: User data dictionary from JWT or database
        
    Returns:
        set: Set of permissions the user has
    """
    # Get base permissions from tier
    tier = user_data.get('tier', 'free')
    permissions = set(TIER_PERMISSIONS.get(tier, set()))
    
    # Add role-specific permissions
    role = user_data.get('role', 'user')
    role_perms = ROLE_PERMISSIONS.get(role, set())
    permissions = permissions.union(role_perms)
    
    return permissions

def has_permission(permission):
    """
    Decorator to check if the user has a specific permission
    
    Args:
        permission: The permission to check for
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get user permissions
            user_permissions = get_user_permissions(g.user)
            
            # Check permission
            if permission not in user_permissions:
                logger.warning(f"Permission denied: {permission} for user {g.user.get('sub')}")
                response = ResponseFormatter.error_response(
                    message=f"You don't have the required permission: {permission}",
                    error_type="authorization_error",
                    error=f"Permission '{permission}' denied",
                    status_code=403,
                    required_permission=permission,
                    start_time=start_time
                )
                return response
            
            # Permission granted, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_any_permission(permissions):
    """
    Decorator to check if the user has any of the specified permissions
    
    Args:
        permissions: List of permissions, any of which grant access
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get user permissions
            user_permissions = get_user_permissions(g.user)
            
            # Check permissions
            for permission in permissions:
                if permission in user_permissions:
                    # User has at least one required permission
                    return f(*args, **kwargs)
            
            # No matching permissions found
            logger.warning(f"Permission denied: User {g.user.get('sub')} has none of the required permissions: {permissions}")
            response = ResponseFormatter.error_response(
                message=f"You don't have any of the required permissions",
                error_type="authorization_error",
                error="Required permissions not granted",
                status_code=403,
                required_permissions=permissions,
                start_time=start_time
            )
            return response
        return decorated_function
    return decorator

def has_all_permissions(permissions):
    """
    Decorator to check if the user has all of the specified permissions
    
    Args:
        permissions: List of permissions, all of which are required
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get user permissions
            user_permissions = get_user_permissions(g.user)
            
            # Check if user has all required permissions
            missing_permissions = [p for p in permissions if p not in user_permissions]
            if missing_permissions:
                logger.warning(f"Permission denied: User {g.user.get('sub')} missing permissions: {missing_permissions}")
                response = ResponseFormatter.error_response(
                    message=f"You don't have all required permissions",
                    error_type="authorization_error",
                    error="Missing required permissions",
                    status_code=403,
                    missing_permissions=missing_permissions,
                    start_time=start_time
                )
                return response
            
            # All permissions granted, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_feature_access(feature_name):
    """
    Decorator to check if user's tier has access to a specific feature
    
    Args:
        feature_name: The feature to check access for
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get user tier
            user_tier = g.user.get('tier', 'free')
            
            # Check feature access based on tier
            tier_features = TIER_FEATURES.get(user_tier, {})
            
            # Special case for advanced_features
            if feature_name == 'advanced_features':
                has_access = tier_features.get('advanced_features', False)
            # Special case for model access
            elif feature_name.startswith('model:'):
                requested_model = feature_name.split(':', 1)[1]
                allowed_models = tier_features.get('model_access', [])
                has_access = requested_model in allowed_models
            # Special case for max_tokens
            elif feature_name.startswith('tokens:'):
                requested_tokens = int(feature_name.split(':', 1)[1])
                max_tokens = tier_features.get('max_tokens', 0)
                has_access = requested_tokens <= max_tokens
            # General feature check
            else:
                has_access = feature_name in tier_features
            
            if not has_access:
                # Get the minimum tier required for this feature
                required_tier = None
                for tier_name, features in TIER_FEATURES.items():
                    if feature_name == 'advanced_features' and features.get('advanced_features', False):
                        required_tier = tier_name
                        break
                    elif feature_name.startswith('model:'):
                        requested_model = feature_name.split(':', 1)[1]
                        if requested_model in features.get('model_access', []):
                            required_tier = tier_name
                            break
                    elif feature_name.startswith('tokens:'):
                        requested_tokens = int(feature_name.split(':', 1)[1])
                        if requested_tokens <= features.get('max_tokens', 0):
                            required_tier = tier_name
                            break
                    elif feature_name in features:
                        required_tier = tier_name
                        break
                
                logger.warning(f"Feature access denied: {feature_name} for user tier {user_tier}")
                response = ResponseFormatter.tier_limit_error(
                    tier=user_tier,
                    required_tier=required_tier,
                    feature=feature_name,
                    message=f"This feature requires {required_tier} tier or higher",
                    error="Feature access denied",
                    upgrade_url="https://techsaas.tech/pricing",
                    status_code=403,
                    start_time=start_time
                )
                return response
            
            # Feature access granted, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def limit_request_rate(limit_per_minute=None, limit_per_hour=None, limit_per_day=None):
    """
    Decorator to enforce request rate limits based on user tier
    
    If multiple time windows are specified, all limits must be satisfied
    
    Args:
        limit_per_minute: Maximum requests per minute (overrides tier-based limits)
        limit_per_hour: Maximum requests per hour (overrides tier-based limits)
        limit_per_day: Maximum requests per day (overrides tier-based limits)
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get user and tier info
            user_id = g.user.get('sub')
            user_tier = g.user.get('tier', 'free')
            tier_features = TIER_FEATURES.get(user_tier, {})
            
            # Get endpoint name for tracking
            endpoint = request.endpoint or request.path
            
            # Check tier-specific rate limits if no override provided
            if limit_per_minute is None and limit_per_hour is None and limit_per_day is None:
                tier_limit = tier_features.get('rate_limit', 0)
                if tier_limit == 0:  # No limit
                    return f(*args, **kwargs)
                
                # Use hourly rate by default
                limit_per_hour = tier_limit
            
            # Current counts (would normally be in Redis or DB)
            # This is a simplified in-memory version
            if not hasattr(g, '_rate_limits'):
                g._rate_limits = {}
            
            # Check minute limit if specified
            if limit_per_minute is not None:
                minute_key = f"{user_id}:{endpoint}:minute:{int(time.time() / 60)}"
                if minute_key not in g._rate_limits:
                    g._rate_limits[minute_key] = 0
                g._rate_limits[minute_key] += 1
                
                if g._rate_limits[minute_key] > limit_per_minute:
                    logger.warning(f"Rate limit exceeded (per minute): {user_id} at {endpoint}")
                    response = ResponseFormatter.tier_limit_error(
                        tier=user_tier,
                        limit_type="requests_per_minute",
                        current_usage=g._rate_limits[minute_key],
                        allowed_limit=limit_per_minute,
                        message=f"Rate limit exceeded: {g._rate_limits[minute_key]}/{limit_per_minute} requests per minute",
                        error="Rate limit exceeded",
                        upgrade_url="https://techsaas.tech/pricing",
                        status_code=429,
                        start_time=start_time
                    )
                    return response
            
            # Check hour limit if specified
            if limit_per_hour is not None:
                hour_key = f"{user_id}:{endpoint}:hour:{int(time.time() / 3600)}"
                if hour_key not in g._rate_limits:
                    g._rate_limits[hour_key] = 0
                g._rate_limits[hour_key] += 1
                
                if g._rate_limits[hour_key] > limit_per_hour:
                    logger.warning(f"Rate limit exceeded (per hour): {user_id} at {endpoint}")
                    response = ResponseFormatter.tier_limit_error(
                        tier=user_tier,
                        limit_type="requests_per_hour",
                        current_usage=g._rate_limits[hour_key],
                        allowed_limit=limit_per_hour,
                        message=f"Rate limit exceeded: {g._rate_limits[hour_key]}/{limit_per_hour} requests per hour",
                        error="Rate limit exceeded",
                        upgrade_url="https://techsaas.tech/pricing",
                        status_code=429,
                        start_time=start_time
                    )
                    return response
            
            # Check day limit if specified
            if limit_per_day is not None:
                day_key = f"{user_id}:{endpoint}:day:{int(time.time() / 86400)}"
                if day_key not in g._rate_limits:
                    g._rate_limits[day_key] = 0
                g._rate_limits[day_key] += 1
                
                if g._rate_limits[day_key] > limit_per_day:
                    logger.warning(f"Rate limit exceeded (per day): {user_id} at {endpoint}")
                    response = ResponseFormatter.tier_limit_error(
                        tier=user_tier,
                        limit_type="requests_per_day",
                        current_usage=g._rate_limits[day_key],
                        allowed_limit=limit_per_day,
                        message=f"Rate limit exceeded: {g._rate_limits[day_key]}/{limit_per_day} requests per day",
                        error="Rate limit exceeded",
                        upgrade_url="https://techsaas.tech/pricing",
                        status_code=429,
                        start_time=start_time
                    )
                    return response
            
            # Rate limit checks passed, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def track_api_usage(category, operation=None, tokens=0):
    """
    Decorator to track API usage for billing and analytics
    
    Args:
        category: Usage category (e.g., 'ai', 'scraping', 'video')
        operation: Specific operation within the category
        tokens: Number of tokens processed (for AI operations)
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Record the start time
            start_time = time.time()
            
            # Call the original function
            response = f(*args, **kwargs)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Get user info if authenticated
            user_id = getattr(g, 'user', {}).get('sub', 'anonymous')
            user_tier = getattr(g, 'user', {}).get('tier', 'free')
            
            # Usage record for logging and billing
            usage_record = {
                'user_id': user_id,
                'tier': user_tier,
                'category': category,
                'operation': operation,
                'tokens': tokens,
                'processing_time': processing_time,
                'endpoint': request.endpoint,
                'method': request.method,
                'ip': request.remote_addr,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Log usage for billing
            logger.info(f"API Usage: {json.dumps(usage_record)}")
            
            # In a real implementation, this would be stored in a database
            # and used for billing calculations
            
            return response
        return decorated_function
    return decorator

def resource_owner(resource_type):
    """
    Decorator to check if user owns a resource or has admin rights
    
    Args:
        resource_type: Type of resource being accessed (e.g., 'project', 'document')
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
            
            # Get resource ID from URL parameters or request data
            resource_id = kwargs.get(f"{resource_type}_id")
            if not resource_id and request.json:
                resource_id = request.json.get(f"{resource_type}_id")
            
            if not resource_id:
                response = ResponseFormatter.error_response(
                    message=f"No {resource_type} ID provided",
                    error_type="validation_error",
                    error="Missing resource ID",
                    status_code=400,
                    start_time=start_time
                )
                return response
            
            # Get user info
            user_id = g.user.get('sub')
            user_role = g.user.get('role', 'user')
            
            # Admins can access any resource
            if user_role in ['admin', 'superadmin']:
                return f(*args, **kwargs)
            
            # Check resource ownership (simplified example - would use DB query)
            # This is a mock implementation - in a real app, you'd query a database
            owner_id = None
            if resource_type == 'project':
                # Mock project ownership check
                # In reality, you'd query a project table in your database
                owner_id = resource_id % 10  # Simple mock
            elif resource_type == 'document':
                # Mock document ownership check
                owner_id = resource_id % 10  # Simple mock
            
            # Convert to strings for comparison
            owner_id = str(owner_id)
            user_id = str(user_id)
            
            # If user doesn't own the resource
            if owner_id != user_id:
                logger.warning(f"Resource access denied: User {user_id} tried to access {resource_type} {resource_id} owned by {owner_id}")
                response = ResponseFormatter.error_response(
                    message=f"You do not have permission to access this {resource_type}",
                    error_type="authorization_error",
                    error="Resource access denied",
                    status_code=403,
                    start_time=start_time
                )
                return response
            
            # User is the resource owner, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_access(level="info", include_body=False):
    """
    Decorator to log all access to an endpoint for audit purposes
    
    Args:
        level: Logging level to use
        include_body: Whether to include request body in logs
        
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user info if authenticated
            user_id = getattr(g, 'user', {}).get('sub', 'anonymous')
            user_role = getattr(g, 'user', {}).get('role', 'anonymous')
            user_tier = getattr(g, 'user', {}).get('tier', 'anonymous')
            
            # Log basic request info
            log_data = {
                'user_id': user_id,
                'role': user_role,
                'tier': user_tier,
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr,
                'user_agent': request.user_agent.string,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add request body if requested (be careful with sensitive data)
            if include_body and request.json:
                # Sanitize any sensitive fields
                body = request.json.copy()
                if 'password' in body:
                    body['password'] = '[REDACTED]'
                if 'token' in body:
                    body['token'] = '[REDACTED]'
                log_data['body'] = body
            
            # Log at appropriate level
            if level == "debug":
                logger.debug(f"API Access: {json.dumps(log_data)}")
            elif level == "info":
                logger.info(f"API Access: {json.dumps(log_data)}")
            elif level == "warning":
                logger.warning(f"API Access: {json.dumps(log_data)}")
            
            # Call the original function
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Register middleware with Flask application
def init_authorization_middleware(app):
    """
    Initialize authorization middleware with a Flask application
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def before_request():
        # Initialize rate limiting for this request
        if not hasattr(g, '_rate_limits'):
            g._rate_limits = {}
    
    @app.after_request
    def after_request(response):
        # Log successful requests to sensitive endpoints
        sensitive_endpoints = [
            '/api/v1/admin',
            '/api/v1/users',
            '/api/v1/subscription',
            '/api/v1/billing'
        ]
        
        endpoint = request.endpoint or ""
        path = request.path or ""
        
        for sensitive in sensitive_endpoints:
            if sensitive in path:
                # Only log successful requests
                if 200 <= response.status_code < 300:
                    # Get user info if authenticated
                    user_id = getattr(g, 'user', {}).get('sub', 'anonymous')
                    user_role = getattr(g, 'user', {}).get('role', 'anonymous')
                    
                    logger.info(f"Sensitive Endpoint Access: user={user_id}, role={user_role}, endpoint={endpoint}, path={path}, method={request.method}, status={response.status_code}")
                break
        
        return response
