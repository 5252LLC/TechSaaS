"""
API Key Management Endpoints

Provides endpoints for creating, listing, and revoking API keys
with comprehensive audit trail integration.
"""

from flask import Blueprint, request, g, jsonify, current_app
import logging
import uuid
from datetime import datetime, timezone

from api.v1.utils.api_key_manager import ApiKeyManager, api_key_auth
from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.middleware.authorization import token_required, has_permission
from api.v1.utils.audit_trail import AuditEvent, get_audit_trail

# Setup logger
logger = logging.getLogger(__name__)

# Create Blueprint
api_key_bp = Blueprint("api_key", __name__, url_prefix="/api/v1/apikeys")

@api_key_bp.route("/", methods=["POST"])
@token_required
def create_api_key():
    """
    Create a new API key
    
    Requires authentication and appropriate permissions.
    The created API key will be returned only once.
    """
    try:
        # Extract user ID from token
        user_id = g.user_id
        
        # Validate request
        if not request.is_json:
            return ResponseFormatter.error("Invalid content type. Expected application/json", 400)
            
        data = request.get_json()
        
        # Validate required fields
        name = data.get("name")
        if not name:
            return ResponseFormatter.error("Missing required field: name", 400)
            
        tier = data.get("tier", "basic")
        if tier not in ["basic", "premium", "enterprise"]:
            return ResponseFormatter.error("Invalid tier. Must be one of: basic, premium, enterprise", 400)
            
        # Get scopes (default to read-only)
        scopes = data.get("scopes", ["read"])
        
        # Create a new API key
        key_manager = ApiKeyManager()
        try:
            key_data = key_manager.create_key(user_id, tier, name, scopes)
            
            # Return the result (this is the only time the full key will be shown)
            return ResponseFormatter.success({
                "message": "API key created successfully",
                "api_key": key_data.get("api_key"),
                "key_id": key_data.get("id"),
                "name": key_data.get("name"),
                "tier": key_data.get("tier"),
                "scopes": key_data.get("scopes"),
                "expires_at": key_data.get("expires_at")
            }, 201)
            
        except Exception as e:
            logger.error(f"Error creating API key: {str(e)}")
            return ResponseFormatter.error(f"Failed to create API key: {str(e)}", 500)
            
    except Exception as e:
        logger.error(f"Unexpected error in create_api_key: {str(e)}")
        
        # Log unexpected error to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=g.user_id if hasattr(g, 'user_id') else "unknown",
                actor_type="user",
                resource_type="api_key",
                resource_id="unknown",
                action="create",
                outcome=AuditEvent.OUTCOME_ERROR,
                details={"error": str(e)},
                sensitivity=AuditEvent.SENSITIVITY_HIGH
            )
            audit_trail.log_event(event)
            
        return ResponseFormatter.error("An unexpected error occurred", 500)

@api_key_bp.route("/", methods=["GET"])
@token_required
def list_api_keys():
    """
    List all API keys for the authenticated user
    
    Returns a list of API keys with metadata (without secrets).
    """
    try:
        # Extract user ID from token
        user_id = g.user_id
        
        # Get API keys for the user
        key_manager = ApiKeyManager()
        keys = key_manager.get_user_keys(user_id)
        
        # Return the result
        return ResponseFormatter.success({
            "api_keys": keys
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in list_api_keys: {str(e)}")
        
        # Log unexpected error to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=g.user_id if hasattr(g, 'user_id') else "unknown",
                actor_type="user",
                resource_type="api_key",
                resource_id="all",
                action="list",
                outcome=AuditEvent.OUTCOME_ERROR,
                details={"error": str(e)},
                sensitivity=AuditEvent.SENSITIVITY_MEDIUM
            )
            audit_trail.log_event(event)
            
        return ResponseFormatter.error("An unexpected error occurred", 500)

@api_key_bp.route("/<key_id>", methods=["DELETE"])
@token_required
def revoke_api_key(key_id):
    """
    Revoke (disable) an API key
    
    Requires authentication. User can only revoke their own API keys.
    """
    try:
        # Extract user ID from token
        user_id = g.user_id
        
        # Validate the key ID format
        try:
            uuid.UUID(key_id)
        except ValueError:
            return ResponseFormatter.error("Invalid API key ID format", 400)
        
        # Revoke the API key
        key_manager = ApiKeyManager()
        success = key_manager.revoke_key(user_id, key_id)
        
        if not success:
            return ResponseFormatter.error("Failed to revoke API key. Key not found or unauthorized.", 404)
            
        # Return success response
        return ResponseFormatter.success({
            "message": "API key revoked successfully"
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in revoke_api_key: {str(e)}")
        
        # Log unexpected error to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=g.user_id if hasattr(g, 'user_id') else "unknown",
                actor_type="user",
                resource_type="api_key",
                resource_id=key_id,
                action="revoke",
                outcome=AuditEvent.OUTCOME_ERROR,
                details={"error": str(e)},
                sensitivity=AuditEvent.SENSITIVITY_HIGH
            )
            audit_trail.log_event(event)
            
        return ResponseFormatter.error("An unexpected error occurred", 500)

@api_key_bp.route("/verify", methods=["POST"])
@api_key_auth(required_scopes=["read"])
def verify_api_key():
    """
    Verify an API key and return its metadata
    
    This endpoint is used to test API key validity and view its metadata.
    The API key is passed in the Authorization header or X-API-Key header.
    """
    try:
        # API key data is set in g by the api_key_auth decorator
        key_data = g.api_key
        
        # Return API key metadata (never return the secret)
        return ResponseFormatter.success({
            "key_id": key_data.get("id"),
            "name": key_data.get("name"),
            "tier": key_data.get("tier"),
            "scopes": key_data.get("scopes"),
            "expires_at": key_data.get("expires_at"),
            "is_enabled": key_data.get("is_enabled")
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in verify_api_key: {str(e)}")
        
        # Log unexpected error to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=g.user_id if hasattr(g, 'user_id') else "unknown",
                actor_type="api_client",
                resource_type="api_key",
                resource_id="unknown",
                action="verify",
                outcome=AuditEvent.OUTCOME_ERROR,
                details={"error": str(e)},
                sensitivity=AuditEvent.SENSITIVITY_MEDIUM
            )
            audit_trail.log_event(event)
            
        return ResponseFormatter.error("An unexpected error occurred", 500)

@api_key_bp.route("/info/<key_id>", methods=["GET"])
@token_required
@has_permission("api_key_management")
def get_api_key_info(key_id):
    """
    Get detailed information about an API key
    
    This endpoint requires authentication and the api_key_management permission.
    It's intended for administrators to view API key details, including usage statistics.
    """
    try:
        # Validate the key ID format
        try:
            uuid.UUID(key_id)
        except ValueError:
            return ResponseFormatter.error("Invalid API key ID format", 400)
            
        # Extract user ID from token
        admin_id = g.user_id
            
        # Connect to database
        from api.v1.utils.database_util import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get API key information
        cursor.execute(
            """
            SELECT ak.id, ak.user_id, ak.name, ak.tier, ak.rate_limit, ak.scopes,
                   ak.created_at, ak.expires_at, ak.last_used_at, ak.is_enabled, ak.revoked_at,
                   u.email, u.username
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.id = %s
            """,
            (key_id,)
        )
        
        key_info = cursor.fetchone()
        
        if not key_info:
            # Log key not found to audit trail
            audit_trail = get_audit_trail()
            if audit_trail:
                event = AuditEvent(
                    event_type=AuditEvent.API_KEY_MANAGEMENT,
                    actor_id=admin_id,
                    actor_type="user",
                    resource_type="api_key",
                    resource_id=key_id,
                    action="info",
                    outcome=AuditEvent.OUTCOME_FAILURE,
                    details={"reason": "key_not_found"},
                    sensitivity=AuditEvent.SENSITIVITY_MEDIUM
                )
                audit_trail.log_event(event)
                
            return ResponseFormatter.error("API key not found", 404)
            
        # Convert to Python types
        key_info['created_at'] = key_info['created_at'].isoformat() if key_info['created_at'] else None
        key_info['expires_at'] = key_info['expires_at'].isoformat() if key_info['expires_at'] else None
        key_info['last_used_at'] = key_info['last_used_at'].isoformat() if key_info['last_used_at'] else None
        key_info['revoked_at'] = key_info['revoked_at'].isoformat() if key_info['revoked_at'] else None
        key_info['scopes'] = key_info['scopes'].split(',') if key_info['scopes'] else []
        
        # Get usage statistics
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_requests,
                AVG(response_time) as avg_response_time,
                MAX(timestamp) as last_request_time,
                COUNT(DISTINCT endpoint) as unique_endpoints
            FROM api_key_usage
            WHERE api_key_id = %s
            """,
            (key_id,)
        )
        
        usage_stats = cursor.fetchone()
        
        # Get recent usage (last 10 requests)
        cursor.execute(
            """
            SELECT endpoint, method, status_code, response_time, ip_address, timestamp
            FROM api_key_usage
            WHERE api_key_id = %s
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (key_id,)
        )
        
        recent_usage = cursor.fetchall()
        
        # Convert timestamp in recent usage
        for usage in recent_usage:
            usage['timestamp'] = usage['timestamp'].isoformat() if usage['timestamp'] else None
        
        # Combine information
        result = {
            "key_info": key_info,
            "usage_stats": usage_stats,
            "recent_usage": recent_usage
        }
        
        # Log admin API key info access to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=admin_id,
                actor_type="user",
                resource_type="api_key",
                resource_id=key_id,
                action="info",
                outcome=AuditEvent.OUTCOME_SUCCESS,
                details={"key_owner": key_info['user_id']},
                sensitivity=AuditEvent.SENSITIVITY_HIGH
            )
            audit_trail.log_event(event)
        
        return ResponseFormatter.success(result)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_api_key_info: {str(e)}")
        
        # Log unexpected error to audit trail
        audit_trail = get_audit_trail()
        if audit_trail:
            event = AuditEvent(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=g.user_id if hasattr(g, 'user_id') else "unknown",
                actor_type="user",
                resource_type="api_key",
                resource_id=key_id,
                action="info",
                outcome=AuditEvent.OUTCOME_ERROR,
                details={"error": str(e)},
                sensitivity=AuditEvent.SENSITIVITY_HIGH
            )
            audit_trail.log_event(event)
            
        return ResponseFormatter.error("An unexpected error occurred", 500)

# Middleware for API key usage tracking
@api_key_bp.before_app_request
def track_api_key_usage():
    """Middleware to track API key usage"""
    # Check if request is using an API key
    if not hasattr(g, 'api_key'):
        return
        
    # Only track if path starts with /api/
    if not request.path.startswith('/api/'):
        return
        
    # Capture request start time
    g.request_start_time = datetime.now(timezone.utc)
    
@api_key_bp.after_app_request
def record_api_key_usage(response):
    """Record API key usage after request completes"""
    # Check if request used an API key and we captured start time
    if not hasattr(g, 'api_key') or not hasattr(g, 'request_start_time'):
        return response
        
    try:
        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time = (end_time - g.request_start_time).total_seconds()
        
        # Get API key data
        key_data = g.api_key
        key_id = key_data.get('id')
        
        # Get request details
        endpoint = request.endpoint
        method = request.method
        status_code = response.status_code
        ip_address = request.remote_addr
        
        # Get request and response size (approximate)
        request_size = int(request.headers.get('Content-Length', 0))
        response_size = int(response.headers.get('Content-Length', 0))
        
        # Generate usage ID
        usage_id = str(uuid.uuid4())
        
        # Record the usage
        from api.v1.utils.database_util import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO api_key_usage 
            (id, api_key_id, endpoint, method, status_code, response_time, 
             request_size, response_size, ip_address, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                usage_id,
                key_id,
                endpoint,
                method,
                status_code,
                response_time,
                request_size,
                response_size,
                ip_address,
                end_time
            )
        )
        
        conn.commit()
        
        # Add usage metrics to audit trail for specific sensitive operations
        if endpoint in ['api_key.create_api_key', 'api_key.revoke_api_key'] or status_code >= 400:
            audit_trail = get_audit_trail()
            if audit_trail:
                outcome = AuditEvent.OUTCOME_SUCCESS
                if status_code >= 400:
                    outcome = AuditEvent.OUTCOME_FAILURE
                    
                event = AuditEvent(
                    event_type=AuditEvent.API_ACCESS,
                    actor_id=key_data.get('user_id'),
                    actor_type="api_client",
                    resource_type="endpoint",
                    resource_id=endpoint,
                    action=method.lower(),
                    outcome=outcome,
                    details={
                        "status_code": status_code,
                        "response_time": response_time,
                        "ip_address": ip_address
                    },
                    sensitivity=AuditEvent.SENSITIVITY_LOW
                )
                audit_trail.log_event(event)
    
    except Exception as e:
        logger.error(f"Error recording API key usage: {str(e)}")
        
    finally:
        return response

def register_api_key_blueprint(app):
    """Register the API key blueprint with the Flask app"""
    app.register_blueprint(api_key_bp)
    
    # Initialize API key database schema
    with app.app_context():
        from api.v1.utils.api_key_manager import init_api_key_schema
        init_api_key_schema()
        
    logger.info("API key blueprint registered")
