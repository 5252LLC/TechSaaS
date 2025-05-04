"""
Authentication endpoints for the TechSaaS API.

This module provides endpoints for user authentication, including:
- User registration
- User login
- Token validation
- Token refresh
- Password reset

All endpoints use standardized response formatting and integrate with the
subscription tier system for access control.
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_smorest import abort
from datetime import datetime, timedelta, timezone, UTC
import time
import hashlib
import secrets
import jwt
import json
import bcrypt
import re
from functools import wraps

# Import shared utilities
from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.utils.validation import validate_json, validate_fields
from api.v1.utils.config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES, JWT_ALGORITHM
from api.v1.utils.database_util import get_db_connection
from api.v1.utils.audit_trail import AuditEvent
from api.v1.middleware.authorization import verify_jwt_token, jwt_required, token_blacklist

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Email validation regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

# Password requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'

# User roles
USER_ROLES = {
    'user': 1,      # Basic user
    'premium': 2,   # Premium subscriber
    'admin': 3,     # Admin user
    'superadmin': 4 # Superadmin with full access
}

# Helper functions
def generate_password_hash(password):
    """Generate a secure password hash using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt)

def check_password_hash(password, password_hash):
    """Check if a password matches a hash."""
    password_bytes = password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8') if isinstance(password_hash, str) else password_hash
    return bcrypt.checkpw(password_bytes, hash_bytes)

def generate_tokens(user_id, email, role, tier):
    """Generate access and refresh tokens."""
    now = datetime.now(UTC)
    
    # Create access token payload
    access_payload = {
        'sub': user_id,
        'email': email,
        'role': role,
        'tier': tier,
        'iat': now,
        'exp': now + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRES),
        'type': 'access',
        'jti': secrets.token_hex(16)  # Add unique JWT ID for blacklisting support
    }
    
    # Create refresh token payload
    refresh_payload = {
        'sub': user_id,
        'email': email,
        'iat': now,
        'exp': now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRES),
        'type': 'refresh',
        'jti': secrets.token_hex(16)  # Add unique JWT ID for blacklisting support
    }
    
    # Generate tokens
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return access_token, refresh_token

def get_user_by_email(email):
    """Get user from database by email."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_by_id(user_id):
    """Get user from database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def blacklist_token(token):
    """Add a token to the blacklist."""
    # Extract JWT ID if available
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        jti = payload.get('jti')
        if jti:
            # In production, store the JTI instead of the full token
            token_blacklist.add(jti)
        else:
            token_blacklist.add(token)
    except:
        # If token can't be decoded, blacklist the full token
        token_blacklist.add(token)
    
    # In production, this would be stored in Redis/database with TTL
    # based on token expiration time

# Role-based access control decorator
def role_required(min_role):
    """Decorator to restrict routes by user role."""
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated_function(*args, **kwargs):
            start_time = datetime.now(UTC).timestamp()
            
            # Check if user has been authenticated by jwt_required
            if not hasattr(g, 'user'):
                return ResponseFormatter.error_response(
                    message="Authentication required",
                    error_type="authentication_error",
                    status_code=401,
                    start_time=start_time
                )
            
            # Get user role from token
            role = g.user.get('role', 'user')
            
            # Get role level 
            user_role_level = USER_ROLES.get(role, 0)
            required_role_level = USER_ROLES.get(min_role, 999)
            
            # Check if user has sufficient role
            if user_role_level < required_role_level:
                # Log failed attempt
                user_id = g.user.get('sub')
                AuditEvent.create(
                    user_id,
                    "authorization_failure", 
                    request.remote_addr,
                    details={
                        "required_role": min_role,
                        "user_role": role,
                        "path": request.path,
                        "method": request.method,
                        "severity": "warning"
                    }
                )
                
                return ResponseFormatter.error_response(
                    message=f"This endpoint requires {min_role} role or higher",
                    error_type="authorization_error",
                    status_code=403,
                    start_time=start_time
                )
            
            # Role check passed, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Subscription tier requirement decorator
def tier_required(required_tier):
    """Decorator to restrict routes by subscription tier."""
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated_function(*args, **kwargs):
            start_time = datetime.now(UTC).timestamp()
            
            # Tier levels
            TIER_LEVELS = {
                'free': 0,
                'basic': 1,
                'premium': 2,
                'professional': 3,
                'enterprise': 4
            }
            
            # Check if user has been authenticated by jwt_required
            if not hasattr(g, 'user'):
                return ResponseFormatter.error_response(
                    message="Authentication required",
                    error_type="authentication_error",
                    status_code=401,
                    start_time=start_time
                )
            
            # Get user tier from token
            tier = g.user.get('tier', 'free')
            
            # Get tier levels
            user_tier_level = TIER_LEVELS.get(tier, 0)
            required_tier_level = TIER_LEVELS.get(required_tier, 999)
            
            # Check if user has sufficient tier
            if user_tier_level < required_tier_level:
                # Admins and superadmins bypass tier restrictions
                role = g.user.get('role', 'user')
                if role in ['admin', 'superadmin']:
                    return f(*args, **kwargs)
                
                # Log failed attempt
                user_id = g.user.get('sub')
                AuditEvent.create(
                    user_id,
                    "authorization_failure", 
                    request.remote_addr,
                    details={
                        "required_tier": required_tier,
                        "user_tier": tier,
                        "path": request.path,
                        "method": request.method,
                        "severity": "warning"
                    }
                )
                
                return ResponseFormatter.tier_limit_error(
                    tier=tier,
                    required_tier=required_tier,
                    status_code=403,
                    start_time=start_time
                )
            
            # Tier check passed, continue
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/register', methods=['POST'])
@validate_json
def register():
    """Register a new user."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            if field not in data:
                return ResponseFormatter.error_response(
                    message=f"Missing required field: {field}",
                    error_type="validation_error",
                    status_code=422,
                    start_time=start_time
                )
        
        # Validate email format
        email = data['email']
        if not re.match(EMAIL_REGEX, email):
            return ResponseFormatter.error_response(
                message="Invalid email format",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Validate password strength
        password = data['password']
        if len(password) < PASSWORD_MIN_LENGTH:
            return ResponseFormatter.error_response(
                message=f"Password must be at least {PASSWORD_MIN_LENGTH} characters",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        if not re.match(PASSWORD_REGEX, password):
            return ResponseFormatter.error_response(
                message="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            return ResponseFormatter.error_response(
                message="Email already registered",
                error_type="validation_error",
                status_code=409,
                start_time=start_time
            )
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Insert user into database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Set default tier and role
        tier = data.get('tier', 'free')
        role = data.get('role', 'user')
        
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, tier, role, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (email, password_hash, data['name'], tier, role, datetime.now(UTC))
        )
        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        # Generate tokens
        access_token, refresh_token = generate_tokens(user_id, email, role, tier)
        
        # Return successful response
        return ResponseFormatter.success_response(
            data={
                'user_id': user_id,
                'email': email,
                'name': data['name'],
                'tier': tier,
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message="User registered successfully",
            metadata={
                'token_expires_in': JWT_ACCESS_TOKEN_EXPIRES * 60  # in seconds
            },
            status_code=201,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Registration error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during registration",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/login', methods=['POST'])
@validate_json
def login():
    """Login a user and return authentication tokens."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password']
        for field in required_fields:
            if field not in data:
                return ResponseFormatter.error_response(
                    message=f"Missing required field: {field}",
                    error_type="validation_error",
                    status_code=422,
                    start_time=start_time
                )
        
        # Get user from database
        user = get_user_by_email(data['email'])
        if not user:
            return ResponseFormatter.error_response(
                message="Invalid email or password",
                error_type="authentication_error",
                status_code=401,
                start_time=start_time
            )
        
        # Verify password
        if not check_password_hash(data['password'], user['password_hash']):
            return ResponseFormatter.error_response(
                message="Invalid email or password",
                error_type="authentication_error",
                status_code=401,
                start_time=start_time
            )
        
        # Generate tokens
        access_token, refresh_token = generate_tokens(
            user['id'], 
            user['email'], 
            user['role'], 
            user['tier']
        )
        
        # Update last login time
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE id = %s",
            (datetime.now(UTC), user['id'])
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        # Return successful response
        return ResponseFormatter.success_response(
            data={
                'user_id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'tier': user['tier'],
                'role': user['role'],
                'access_token': access_token,
                'refresh_token': refresh_token
            },
            message="Login successful",
            metadata={
                'token_expires_in': JWT_ACCESS_TOKEN_EXPIRES * 60,  # in seconds
                'subscription_status': 'active',
                'last_login': user.get('last_login', 'First login')
            },
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Login error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during login",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/refresh', methods=['POST'])
@validate_json
def refresh_token():
    """Refresh access token using refresh token."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if 'refresh_token' not in data:
            return ResponseFormatter.error_response(
                message="Missing refresh token",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Verify refresh token
        payload = verify_jwt_token(data['refresh_token'], token_type='refresh')
        if not payload:
            return ResponseFormatter.error_response(
                message="Invalid or expired refresh token",
                error_type="authentication_error",
                status_code=401,
                start_time=start_time
            )
        
        # Get user from database
        user = get_user_by_id(payload['sub'])
        if not user:
            return ResponseFormatter.error_response(
                message="User not found",
                error_type="authentication_error",
                status_code=401,
                start_time=start_time
            )
        
        # Generate new access token
        access_token, _ = generate_tokens(
            user['id'], 
            user['email'], 
            user['role'], 
            user['tier']
        )
        
        # Return successful response
        return ResponseFormatter.success_response(
            data={
                'access_token': access_token
            },
            message="Token refreshed successfully",
            metadata={
                'token_expires_in': JWT_ACCESS_TOKEN_EXPIRES * 60  # in seconds
            },
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Token refresh error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during token refresh",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """Logout a user by invalidating their tokens."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1]
        
        # Add token to blacklist
        blacklist_token(token)
        
        # Return successful response
        return ResponseFormatter.success_response(
            message="Logged out successfully",
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Logout error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during logout",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/verify', methods=['GET'])
@jwt_required
def verify_authentication():
    """Verify user authentication and return user details."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get user from context (set by jwt_required decorator)
        user_data = g.user
        
        # Return successful response
        return ResponseFormatter.success_response(
            data={
                'user_id': user_data['sub'],
                'email': user_data['email'],
                'role': user_data['role'],
                'tier': user_data['tier']
            },
            message="Authentication valid",
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Verify authentication error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred while verifying authentication",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/password/reset-request', methods=['POST'])
@validate_json
def request_password_reset():
    """Request a password reset token."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        if 'email' not in data:
            return ResponseFormatter.error_response(
                message="Email is required",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Check if user exists
        user = get_user_by_email(data['email'])
        if not user:
            # Return success even if user doesn't exist (security best practice)
            return ResponseFormatter.success_response(
                message="If your email is registered, you will receive a password reset link",
                status_code=200,
                start_time=start_time
            )
        
        # Generate reset token (in a real implementation, this would be stored in the database)
        reset_token = secrets.token_urlsafe(32)
        reset_token_expiry = datetime.now(UTC) + timedelta(hours=1)
        
        # In a real implementation, you would store the token and send an email
        
        # Return successful response
        return ResponseFormatter.success_response(
            message="If your email is registered, you will receive a password reset link",
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Password reset request error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during password reset request",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

@auth_bp.route('/password/reset', methods=['POST'])
@validate_json
def reset_password():
    """Reset password using a reset token."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['token', 'email', 'new_password']
        for field in required_fields:
            if field not in data:
                return ResponseFormatter.error_response(
                    message=f"Missing required field: {field}",
                    error_type="validation_error",
                    status_code=422,
                    start_time=start_time
                )
        
        # Validate password strength
        password = data['new_password']
        if len(password) < PASSWORD_MIN_LENGTH:
            return ResponseFormatter.error_response(
                message=f"Password must be at least {PASSWORD_MIN_LENGTH} characters",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        if not re.match(PASSWORD_REGEX, password):
            return ResponseFormatter.error_response(
                message="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # In a real implementation, you would verify the token against the database
        # For demo purposes, we'll just simulate success
        
        # Return successful response
        return ResponseFormatter.success_response(
            message="Password reset successful. You can now login with your new password.",
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Password reset error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred during password reset",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

# Protected route example with role requirement
@auth_bp.route('/admin/users', methods=['GET'])
@jwt_required
@role_required('admin')
def get_all_users():
    """Get all users (admin only)."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # In a real implementation, you would fetch users from the database
        # For demo purposes, we'll return mock data
        users = [
            {
                'id': 1,
                'email': 'admin@techsaas.tech',
                'name': 'Admin User',
                'tier': 'enterprise',
                'role': 'admin',
                'created_at': '2025-01-01T00:00:00Z'
            },
            {
                'id': 2,
                'email': 'user@techsaas.tech',
                'name': 'Regular User',
                'tier': 'basic',
                'role': 'user',
                'created_at': '2025-01-02T00:00:00Z'
            }
        ]
        
        # Return successful response
        return ResponseFormatter.success_response(
            data=users,
            message="Users retrieved successfully",
            metadata={
                'total_users': len(users)
            },
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Get users error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred while retrieving users",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

# Protected route example with tier requirement
@auth_bp.route('/premium-features', methods=['GET'])
@jwt_required
@tier_required('premium')
def get_premium_features():
    """Get premium features (premium tier or higher only)."""
    start_time = datetime.now(UTC).timestamp()
    
    try:
        # Return premium features
        features = [
            {
                'id': 1,
                'name': 'Advanced AI Processing',
                'description': 'Access to more powerful AI models and longer context windows'
            },
            {
                'id': 2,
                'name': 'Unlimited API Calls',
                'description': 'Make unlimited API calls to our endpoints'
            },
            {
                'id': 3,
                'name': 'Priority Support',
                'description': '24/7 priority support for all your needs'
            }
        ]
        
        # Return successful response
        return ResponseFormatter.success_response(
            data=features,
            message="Premium features retrieved successfully",
            metadata={
                'tier': g.user['tier']
            },
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Log exception
        current_app.logger.error(f"Get premium features error: {str(e)}")
        
        # Return error response
        return ResponseFormatter.error_response(
            message="An error occurred while retrieving premium features",
            error_type="server_error",
            status_code=500,
            start_time=start_time
        )

# Health check endpoint (public)
@auth_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the authentication service."""
    start_time = datetime.now(UTC).timestamp()
    
    return ResponseFormatter.success_response(
        data={
            'service': 'Authentication Service',
            'status': 'operational',
            'timestamp': datetime.now(UTC).isoformat()
        },
        message="Authentication service is healthy",
        status_code=200,
        start_time=start_time
    )
