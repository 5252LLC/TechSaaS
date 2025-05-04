"""
API Key Management Module

Provides secure creation, validation, and management of API keys
for external developers integrating with the TechSaaS platform.
Includes comprehensive audit trail integration for security and compliance.
"""

import secrets
import hashlib
import base64
import time
from datetime import datetime, timezone, timedelta
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union

from api.v1.utils.audit_trail import AuditEvent, get_audit_trail
from api.v1.utils.database_util import get_db_connection

# Setup logger
logger = logging.getLogger(__name__)

# API Key patterns and settings
API_KEY_PREFIX = "tsk"  # TechSaaS Key prefix
API_KEY_ENTROPY_BYTES = 24  # 192 bits of entropy for the key
API_KEY_PARTS = 3  # Format: prefix.id.secret
API_KEY_SEPARATOR = "."
API_KEY_EXPIRY_DAYS = {
    "basic": 365,      # 1 year
    "premium": 730,    # 2 years
    "enterprise": 1095 # 3 years
}

# API Key rate limits (requests per minute)
API_KEY_RATE_LIMITS = {
    "basic": 60,       # 1 request per second
    "premium": 300,    # 5 requests per second
    "enterprise": 1200 # 20 requests per second
}

class ApiKeyManager:
    """Manages API key operations with audit trail integration"""
    
    def __init__(self, db=None):
        """Initialize API key manager"""
        self.db = db
        
    def create_key(self, user_id: str, tier: str, name: str, scopes: List[str]) -> Dict[str, Any]:
        """
        Create a new API key for a user
        
        Args:
            user_id: ID of the user creating the key
            tier: Tier of the API key (basic, premium, enterprise)
            name: Friendly name for the key
            scopes: List of permission scopes for the key
            
        Returns:
            Dictionary containing key information including the raw API key
            (this is the only time the full key will be returned)
        """
        # Generate a unique ID for the key
        key_id = str(uuid.uuid4())
        
        # Generate a secure random secret
        key_secret = secrets.token_hex(API_KEY_ENTROPY_BYTES)
        
        # Create the full key string
        api_key = f"{API_KEY_PREFIX}{API_KEY_SEPARATOR}{key_id}{API_KEY_SEPARATOR}{key_secret}"
        
        # Hash the secret for storage (we never store the raw secret)
        secret_hash = self._hash_secret(key_secret)
        
        # Generate expiry date based on tier
        days = API_KEY_RATE_LIMITS.get(tier, 365)
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        
        # Get rate limit based on tier
        rate_limit = API_KEY_RATE_LIMITS.get(tier, 60)
        
        # Store the key in the database
        try:
            conn = self.db or get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO api_keys 
                (id, user_id, name, secret_hash, tier, rate_limit, scopes, 
                 created_at, expires_at, last_used_at, is_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, 1)
                """,
                (
                    key_id, 
                    user_id, 
                    name, 
                    secret_hash, 
                    tier, 
                    rate_limit,
                    ",".join(scopes),
                    datetime.now(timezone.utc),
                    expiry
                )
            )
            
            conn.commit()
            
            # Create audit event for API key creation
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="create",
                    outcome=AuditEvent.OUTCOME_SUCCESS,
                    details={
                        "name": name, 
                        "tier": tier,
                        "scopes": scopes,
                        "expires_at": expiry.isoformat()
                    },
                    sensitivity=AuditEvent.SENSITIVITY_HIGH
                )
                audit_trail.log_event(event)
            
            # Return the API key information
            return {
                "id": key_id,
                "name": name,
                "api_key": api_key,  # Only time the full key is returned
                "tier": tier,
                "rate_limit": rate_limit,
                "scopes": scopes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expiry.isoformat(),
                "is_enabled": True
            }
            
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            
            # Log the error to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="create",
                    outcome=AuditEvent.OUTCOME_ERROR,
                    details={"error": str(e)},
                    sensitivity=AuditEvent.SENSITIVITY_HIGH
                )
                audit_trail.log_event(event)
                
            # Re-raise the exception
            raise
            
    def validate_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key and return its details if valid
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, key_details)
        """
        # Parse the key
        try:
            prefix, key_id, key_secret = api_key.split(API_KEY_SEPARATOR)
            
            if prefix != API_KEY_PREFIX:
                logger.warning(f"Invalid API key prefix: {prefix}")
                return False, None
                
        except ValueError:
            logger.warning("Invalid API key format")
            return False, None
            
        # Hash the secret
        secret_hash = self._hash_secret(key_secret)
        
        # Look up the key in the database
        try:
            conn = self.db or get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute(
                """
                SELECT id, user_id, name, tier, rate_limit, scopes, 
                       created_at, expires_at, last_used_at, is_enabled
                FROM api_keys
                WHERE id = %s AND secret_hash = %s
                """,
                (key_id, secret_hash)
            )
            
            key_data = cursor.fetchone()
            
            if not key_data:
                # Log invalid key attempt to audit trail
                audit_trail = get_audit_trail()
                if audit_trail:
                    event = AuditEvent(
                        event_type=AuditEvent.API_KEY_MANAGEMENT,
                        actor_id="unknown",
                        actor_type="api_client",
                        resource_type="api_key",
                        resource_id=key_id,
                        action="validate",
                        outcome=AuditEvent.OUTCOME_FAILURE,
                        details={"reason": "invalid_key"},
                        sensitivity=AuditEvent.SENSITIVITY_HIGH
                    )
                    audit_trail.log_event(event)
                    
                return False, None
                
            # Convert to Python types
            key_data['created_at'] = key_data['created_at'].isoformat() if key_data['created_at'] else None
            key_data['expires_at'] = key_data['expires_at'].isoformat() if key_data['expires_at'] else None
            key_data['last_used_at'] = key_data['last_used_at'].isoformat() if key_data['last_used_at'] else None
            key_data['scopes'] = key_data['scopes'].split(',') if key_data['scopes'] else []
            
            # Check if key is enabled
            if not key_data['is_enabled']:
                # Log disabled key attempt to audit trail
                audit_trail = get_audit_trail()
                if audit_trail:
                    event = AuditEvent(
                        event_type=AuditEvent.API_KEY_MANAGEMENT,
                        actor_id=key_data['user_id'],
                        actor_type="api_client",
                        resource_type="api_key",
                        resource_id=key_id,
                        action="validate",
                        outcome=AuditEvent.OUTCOME_FAILURE,
                        details={"reason": "key_disabled"},
                        sensitivity=AuditEvent.SENSITIVITY_HIGH
                    )
                    audit_trail.log_event(event)
                    
                return False, None
                
            # Check if key is expired
            if key_data['expires_at']:
                expires_at = datetime.fromisoformat(key_data['expires_at'].replace('Z', '+00:00'))
                if expires_at < datetime.now(timezone.utc):
                    # Log expired key attempt to audit trail
                    audit_trail = get_audit_trail()
                    if audit_trail:
                        event = AuditEvent(
                            event_type=AuditEvent.API_KEY_MANAGEMENT,
                            actor_id=key_data['user_id'],
                            actor_type="api_client",
                            resource_type="api_key",
                            resource_id=key_id,
                            action="validate",
                            outcome=AuditEvent.OUTCOME_FAILURE,
                            details={"reason": "key_expired"},
                            sensitivity=AuditEvent.SENSITIVITY_HIGH
                        )
                        audit_trail.log_event(event)
                        
                    return False, None
            
            # Update last used timestamp
            cursor.execute(
                "UPDATE api_keys SET last_used_at = %s WHERE id = %s",
                (datetime.now(timezone.utc), key_id)
            )
            
            conn.commit()
            
            # Log successful key validation to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=key_data['user_id'],
                    actor_type="api_client",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="validate",
                    outcome=AuditEvent.OUTCOME_SUCCESS,
                    details={},
                    sensitivity=AuditEvent.SENSITIVITY_MEDIUM
                )
                audit_trail.log_event(event)
                
            return True, key_data
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            
            # Log error to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id="unknown",
                    actor_type="api_client",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="validate",
                    outcome=AuditEvent.OUTCOME_ERROR,
                    details={"error": str(e)},
                    sensitivity=AuditEvent.SENSITIVITY_HIGH
                )
                audit_trail.log_event(event)
                
            return False, None
            
    def revoke_key(self, user_id: str, key_id: str) -> bool:
        """
        Revoke (disable) an API key
        
        Args:
            user_id: ID of the user revoking the key
            key_id: ID of the key to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.db or get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # First, check if the key exists and belongs to the user
            cursor.execute(
                "SELECT user_id FROM api_keys WHERE id = %s",
                (key_id,)
            )
            
            key_data = cursor.fetchone()
            
            if not key_data:
                # Log key not found to audit trail
                audit_trail = get_audit_trail()
                if audit_trail:
                    event = AuditEvent(
                        event_type=AuditEvent.API_KEY_MANAGEMENT,
                        actor_id=user_id,
                        actor_type="user",
                        resource_type="api_key",
                        resource_id=key_id,
                        action="revoke",
                        outcome=AuditEvent.OUTCOME_FAILURE,
                        details={"reason": "key_not_found"},
                        sensitivity=AuditEvent.SENSITIVITY_HIGH
                    )
                    audit_trail.log_event(event)
                    
                return False
                
            # Check if the user is authorized to revoke this key
            key_user_id = key_data['user_id']
            if key_user_id != user_id:
                # Log unauthorized revocation attempt to audit trail
                audit_trail = get_audit_trail()
                if audit_trail:
                    event = AuditEvent(
                        event_type=AuditEvent.API_KEY_MANAGEMENT,
                        actor_id=user_id,
                        actor_type="user",
                        resource_type="api_key",
                        resource_id=key_id,
                        action="revoke",
                        outcome=AuditEvent.OUTCOME_FAILURE,
                        details={
                            "reason": "unauthorized",
                            "key_owner": key_user_id
                        },
                        sensitivity=AuditEvent.SENSITIVITY_CRITICAL
                    )
                    audit_trail.log_event(event)
                    
                return False
                
            # Revoke the key
            cursor.execute(
                "UPDATE api_keys SET is_enabled = 0, revoked_at = %s WHERE id = %s",
                (datetime.now(timezone.utc), key_id)
            )
            
            conn.commit()
            
            # Log successful key revocation to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="revoke",
                    outcome=AuditEvent.OUTCOME_SUCCESS,
                    details={},
                    sensitivity=AuditEvent.SENSITIVITY_HIGH
                )
                audit_trail.log_event(event)
                
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            
            # Log error to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="revoke",
                    outcome=AuditEvent.OUTCOME_ERROR,
                    details={"error": str(e)},
                    sensitivity=AuditEvent.SENSITIVITY_HIGH
                )
                audit_trail.log_event(event)
                
            return False
            
    def get_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all API keys for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of API key details (without secrets)
        """
        try:
            conn = self.db or get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute(
                """
                SELECT id, name, tier, rate_limit, scopes, 
                       created_at, expires_at, last_used_at, is_enabled, revoked_at
                FROM api_keys
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            
            keys = cursor.fetchall()
            
            # Convert to Python types
            for key in keys:
                key['created_at'] = key['created_at'].isoformat() if key['created_at'] else None
                key['expires_at'] = key['expires_at'].isoformat() if key['expires_at'] else None
                key['last_used_at'] = key['last_used_at'].isoformat() if key['last_used_at'] else None
                key['revoked_at'] = key['revoked_at'].isoformat() if key['revoked_at'] else None
                key['scopes'] = key['scopes'].split(',') if key['scopes'] else []
            
            # Log user keys retrieval to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id="all",
                    action="list",
                    outcome=AuditEvent.OUTCOME_SUCCESS,
                    details={"count": len(keys)},
                    sensitivity=AuditEvent.SENSITIVITY_MEDIUM
                )
                audit_trail.log_event(event)
                
            return keys
            
        except Exception as e:
            logger.error(f"Error getting user API keys: {str(e)}")
            
            # Log error to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=user_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id="all",
                    action="list",
                    outcome=AuditEvent.OUTCOME_ERROR,
                    details={"error": str(e)},
                    sensitivity=AuditEvent.SENSITIVITY_MEDIUM
                )
                audit_trail.log_event(event)
                
            return []
            
    def _hash_secret(self, secret: str) -> str:
        """Hash an API key secret for storage"""
        # Use a proper key derivation function for hashing
        return hashlib.sha256(secret.encode()).hexdigest()

# API Key middleware
def api_key_auth(required_scopes=None):
    """
    Decorator to require API key authentication with specific scopes
    
    Args:
        required_scopes: List of required scopes (or None for any scope)
        
    Returns:
        Decorated function
    """
    from functools import wraps
    from flask import request, g, current_app
    
    from api.v1.utils.response_formatter import ResponseFormatter
    
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get API key from request
            api_key = None
            
            # Check Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                api_key = auth_header.split(' ')[1]
                
            # Check X-API-Key header
            if not api_key:
                api_key = request.headers.get('X-API-Key')
                
            # Check query parameter
            if not api_key:
                api_key = request.args.get('api_key')
            
            if not api_key:
                # Log missing API key to audit trail
                audit_trail = get_audit_trail()
                ip_address = request.remote_addr
                endpoint = request.endpoint
                
                if audit_trail:
                    event = AuditEvent(
                        event_type=AuditEvent.API_KEY_MANAGEMENT,
                        actor_id="anonymous",
                        actor_type="api_client",
                        resource_type="endpoint",
                        resource_id=endpoint,
                        action="access",
                        outcome=AuditEvent.OUTCOME_FAILURE,
                        details={"reason": "missing_api_key", "ip_address": ip_address},
                        sensitivity=AuditEvent.SENSITIVITY_MEDIUM
                    )
                    audit_trail.log_event(event)
                    
                return ResponseFormatter.error("API key required", 401)
            
            # Validate the API key
            key_manager = ApiKeyManager()
            is_valid, key_data = key_manager.validate_key(api_key)
            
            if not is_valid or not key_data:
                # Audit trail already logged in validate_key method
                return ResponseFormatter.error("Invalid API key", 401)
            
            # Check scopes if required
            if required_scopes:
                key_scopes = key_data.get('scopes', [])
                missing_scopes = [s for s in required_scopes if s not in key_scopes]
                
                if missing_scopes:
                    # Log insufficient scopes to audit trail
                    audit_trail = get_audit_trail()
                    if audit_trail:
                        event = AuditEvent(
                            event_type=AuditEvent.API_KEY_MANAGEMENT,
                            actor_id=key_data.get('user_id'),
                            actor_type="api_client",
                            resource_type="scope",
                            resource_id=",".join(missing_scopes),
                            action="check_scope",
                            outcome=AuditEvent.OUTCOME_FAILURE,
                            details={
                                "required_scopes": required_scopes,
                                "key_scopes": key_scopes
                            },
                            sensitivity=AuditEvent.SENSITIVITY_HIGH
                        )
                        audit_trail.log_event(event)
                        
                    return ResponseFormatter.error(
                        f"API key does not have required scopes: {', '.join(missing_scopes)}", 
                        403
                    )
            
            # Set API key data in request context
            g.api_key = key_data
            g.user_id = key_data.get('user_id')
            g.api_tier = key_data.get('tier')
            
            # Execute the decorated function
            return f(*args, **kwargs)
            
        return decorated
    
    return decorator

# Initialize database schema for API keys
def init_api_key_schema(db=None):
    """Initialize the database schema for API keys"""
    try:
        conn = db or get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            name VARCHAR(100) NOT NULL,
            secret_hash VARCHAR(64) NOT NULL,
            tier VARCHAR(20) NOT NULL,
            rate_limit INT NOT NULL,
            scopes TEXT,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP,
            last_used_at TIMESTAMP,
            revoked_at TIMESTAMP,
            is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            INDEX (user_id),
            INDEX (secret_hash)
        )
        ''')
        
        # Create audit log table for API key usage
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_key_usage (
            id VARCHAR(36) PRIMARY KEY,
            api_key_id VARCHAR(36) NOT NULL,
            endpoint VARCHAR(255) NOT NULL,
            method VARCHAR(10) NOT NULL,
            status_code INT NOT NULL,
            response_time FLOAT NOT NULL,
            request_size INT,
            response_size INT,
            ip_address VARCHAR(45),
            timestamp TIMESTAMP NOT NULL,
            INDEX (api_key_id),
            INDEX (timestamp),
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        )
        ''')
        
        conn.commit()
        logger.info("API key schema initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing API key schema: {str(e)}")
        raise
