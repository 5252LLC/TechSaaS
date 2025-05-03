"""
Role-Based Access Control (RBAC) System
Implements comprehensive role-based access control for the TechSaaS API.
Works with the JWT authentication and authorization middleware.
"""

import logging
from functools import wraps
from flask import request, g, current_app
from datetime import datetime

from api.v1.utils.response_formatter import ResponseFormatter

# Setup logger
logger = logging.getLogger(__name__)

# Define roles and their hierarchy
ROLE_HIERARCHY = {
    'user': 0,
    'premium': 1,
    'admin': 2,
    'superadmin': 3
}

# Define admin areas with required role levels
ADMIN_AREAS = {
    'metrics': 1,      # premium users can view basic metrics
    'users': 2,        # admin role required
    'billing': 2,      # admin role required
    'system': 3,       # superadmin role required
    'security': 3      # superadmin role required
}

def get_role_level(role):
    """
    Get the numeric level of a role
    
    Args:
        role (str): Role name
        
    Returns:
        int: Role level, 0 if role not found
    """
    return ROLE_HIERARCHY.get(role, 0)

def requires_role(required_role):
    """
    Decorator to check if a user has a specific role or higher
    
    Args:
        required_role (str): The minimum role required
        
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
            
            # Get user role
            user_role = g.user.get('role', 'user')
            
            # Get numeric levels
            user_level = get_role_level(user_role)
            required_level = get_role_level(required_role)
            
            # Check if user role is sufficient
            if user_level < required_level:
                logger.warning(f"Role access denied: User with role '{user_role}' (level {user_level}) tried to access endpoint requiring '{required_role}' (level {required_level})")
                response = ResponseFormatter.error_response(
                    message=f"This endpoint requires '{required_role}' role or higher",
                    error_type="authorization_error",
                    error="Insufficient role privileges",
                    status_code=403,
                    user_role=user_role,
                    required_role=required_role,
                    start_time=start_time
                )
                return response
            
            # Role is sufficient, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_admin_access(area):
    """
    Decorator to check if a user has access to a specific admin area
    
    Args:
        area (str): Admin area name
        
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
            
            # Get user role
            user_role = g.user.get('role', 'user')
            
            # Get numeric levels
            user_level = get_role_level(user_role)
            required_level = ADMIN_AREAS.get(area, 3)  # Default to superadmin if area not found
            
            # Check if user role is sufficient
            if user_level < required_level:
                logger.warning(f"Admin area access denied: User with role '{user_role}' (level {user_level}) tried to access admin area '{area}' requiring level {required_level}")
                
                # Determine which role is required based on level
                required_role = "superadmin"  # Default
                for role, level in ROLE_HIERARCHY.items():
                    if level == required_level:
                        required_role = role
                        break
                
                response = ResponseFormatter.error_response(
                    message=f"Access to admin area '{area}' requires '{required_role}' role or higher",
                    error_type="authorization_error",
                    error="Admin area access denied",
                    status_code=403,
                    user_role=user_role,
                    required_role=required_role,
                    admin_area=area,
                    start_time=start_time
                )
                return response
            
            # Role is sufficient, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def protect_admin_route():
    """
    Generic decorator to protect admin routes with sensible defaults
    
    Requires admin role and logs all access attempts
    
    Returns:
        function: Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now().timestamp()
            
            # Check if user is authenticated
            if not hasattr(g, 'user'):
                logger.warning(f"Unauthenticated admin access attempt to {request.path}")
                response = ResponseFormatter.error_response(
                    message="Authentication required for admin access",
                    error_type="authentication_error",
                    error="No valid authentication token provided",
                    status_code=401,
                    start_time=start_time
                )
                return response
            
            # Get user role
            user_role = g.user.get('role', 'user')
            user_id = g.user.get('sub', 'unknown')
            
            # Check if user is an admin
            if user_role not in ['admin', 'superadmin']:
                logger.warning(f"Unauthorized admin access attempt: User {user_id} with role {user_role} tried to access {request.path}")
                response = ResponseFormatter.error_response(
                    message="Admin access required",
                    error_type="authorization_error",
                    error="Insufficient role privileges",
                    status_code=403,
                    start_time=start_time
                )
                return response
            
            # Log successful admin access
            logger.info(f"Admin access: User {user_id} with role {user_role} accessed {request.path}")
            
            # Admin access granted, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_or_owner(owner_id_param):
    """
    Decorator to check if user is an admin or the owner of a resource
    
    Args:
        owner_id_param (str): Parameter name containing the owner ID
        
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
            
            # Get user info
            user_id = g.user.get('sub')
            user_role = g.user.get('role', 'user')
            
            # Admins can access regardless of ownership
            if user_role in ['admin', 'superadmin']:
                return f(*args, **kwargs)
            
            # Get owner ID from URL parameters or request data
            owner_id = kwargs.get(owner_id_param)
            if not owner_id and request.json:
                owner_id = request.json.get(owner_id_param)
            
            # If no owner ID found, assume it's not a user-specific resource
            if not owner_id:
                response = ResponseFormatter.error_response(
                    message=f"No {owner_id_param} provided",
                    error_type="validation_error",
                    error="Missing resource identifier",
                    status_code=400,
                    start_time=start_time
                )
                return response
            
            # Convert to strings for comparison
            owner_id = str(owner_id)
            user_id = str(user_id)
            
            # Check if user is the owner
            if owner_id != user_id:
                logger.warning(f"Resource access denied: User {user_id} tried to access resource owned by {owner_id}")
                response = ResponseFormatter.error_response(
                    message="You do not have permission to access this resource",
                    error_type="authorization_error",
                    error="Resource access denied",
                    status_code=403,
                    start_time=start_time
                )
                return response
            
            # User is the owner, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_access_matrix(role_access_map):
    """
    Decorator to enforce complex role-action access control
    
    Args:
        role_access_map (dict): Map of roles to allowed actions
        
    Example:
        @role_access_matrix({
            'user': ['read'],
            'premium': ['read', 'write'],
            'admin': ['read', 'write', 'delete']
        })
        def resource_endpoint():
            action = request.args.get('action', 'read')
            # Function body...
    
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
            
            # Get user role and requested action
            user_role = g.user.get('role', 'user')
            action = request.args.get('action', 'read')
            
            # If superadmin, allow all actions
            if user_role == 'superadmin':
                return f(*args, **kwargs)
            
            # Check if role exists in the access map
            if user_role not in role_access_map:
                logger.warning(f"Role not in access matrix: {user_role}")
                response = ResponseFormatter.error_response(
                    message="Your role does not have any permissions for this resource",
                    error_type="authorization_error",
                    error="Role not authorized",
                    status_code=403,
                    start_time=start_time
                )
                return response
            
            # Check if action is allowed for role
            allowed_actions = role_access_map.get(user_role, [])
            if action not in allowed_actions:
                logger.warning(f"Action not allowed: User with role {user_role} attempted {action} but is only allowed {allowed_actions}")
                response = ResponseFormatter.error_response(
                    message=f"Your role '{user_role}' is not allowed to perform the '{action}' action",
                    error_type="authorization_error",
                    error="Action not allowed",
                    status_code=403,
                    allowed_actions=allowed_actions,
                    requested_action=action,
                    start_time=start_time
                )
                return response
            
            # Action is allowed, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Additional helper functions for the RBAC system

def get_user_roles():
    """
    Get all defined user roles
    
    Returns:
        list: List of role names
    """
    return list(ROLE_HIERARCHY.keys())

def get_admin_areas():
    """
    Get all defined admin areas with their required roles
    
    Returns:
        dict: Map of admin areas to required role names
    """
    role_map = {}
    for area, level in ADMIN_AREAS.items():
        for role, role_level in ROLE_HIERARCHY.items():
            if role_level == level:
                role_map[area] = role
                break
    
    return role_map

def upgrade_required_response(current_tier, required_tier, feature_name):
    """
    Generate a standardized upgrade required response
    
    Args:
        current_tier (str): User's current tier
        required_tier (str): Tier required for access
        feature_name (str): Name of the feature being accessed
        
    Returns:
        tuple: Response object and status code
    """
    start_time = datetime.now().timestamp()
    
    return ResponseFormatter.tier_limit_error(
        tier=current_tier,
        required_tier=required_tier,
        feature=feature_name,
        message=f"The {feature_name} feature requires {required_tier} tier or higher",
        upgrade_url="https://techsaas.tech/pricing",
        status_code=403,
        start_time=start_time
    ), 403
