"""
API Monetization Routes

This module provides routes for API monetization, including API key management,
subscription tiers, and usage tracking.
"""

import time
import logging
import uuid
from flask import Blueprint, jsonify, request, g, current_app, render_template
from middleware.security import jwt_required, roles_required
from middleware.response_transform import standardize_response
from utils.db_connector import get_db_connector

logger = logging.getLogger("api_gateway.monetization")

# Create blueprint
monetization_blueprint = Blueprint('monetization', __name__, url_prefix='/api/monetization')

# Subscription tiers with rate limits and features
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free Tier",
        "description": "Basic access for evaluation and personal projects",
        "rate_limit": 60,  # Requests per minute
        "features": [
            "Basic API access",
            "Public data only",
            "Community support"
        ],
        "price": {
            "amount": 0,
            "currency": "USD",
            "interval": "month"
        }
    },
    "basic": {
        "name": "Basic Tier",
        "description": "Enhanced access for startups and small businesses",
        "rate_limit": 300,  # Requests per minute
        "features": [
            "Full API access",
            "Advanced data access",
            "Email support",
            "Analytics dashboard"
        ],
        "price": {
            "amount": 49,
            "currency": "USD",
            "interval": "month"
        }
    },
    "professional": {
        "name": "Professional Tier",
        "description": "High-volume access for growing businesses",
        "rate_limit": 1000,  # Requests per minute
        "features": [
            "Full API access",
            "Premium data access",
            "Priority support",
            "Advanced analytics",
            "Customizable rate limits"
        ],
        "price": {
            "amount": 199,
            "currency": "USD",
            "interval": "month"
        }
    },
    "enterprise": {
        "name": "Enterprise Tier",
        "description": "Unlimited access for large organizations",
        "rate_limit": 5000,  # Requests per minute
        "features": [
            "Full API access",
            "Premium data access",
            "Dedicated support",
            "Custom solutions",
            "Service level agreement",
            "Custom rate limits"
        ],
        "price": {
            "amount": "Custom",
            "currency": "USD",
            "interval": "month"
        }
    }
}

@monetization_blueprint.route('/tiers')
@standardize_response
def list_tiers():
    """List available subscription tiers (JSON API endpoint)"""
    db = get_db_connector()
    tiers = db.get_subscription_tiers()
    
    # Return JSON for API clients
    return {
        "count": len(tiers),
        "tiers": tiers
    }

@monetization_blueprint.route('/tiers/view', methods=['GET'])
def view_tiers():
    """Render HTML view of subscription tiers for browsers"""
    db = get_db_connector()
    tiers = db.get_subscription_tiers()
    return render_template('tiers.html', tiers=tiers)

@monetization_blueprint.route('/tier/<tier_id>')
@standardize_response
def get_tier(tier_id):
    """Get details for a specific tier"""
    db = get_db_connector()
    tier = db.get_subscription_tier(tier_id.lower())
    
    if not tier:
        return {"error": f"Unknown tier: {tier_id}"}, 404
    
    return {"tier": tier}

@monetization_blueprint.route('/keys', methods=['GET'])
@jwt_required
@standardize_response
def list_api_keys():
    """List API keys for the authenticated user"""
    user_id = g.user
    db = get_db_connector()
    
    # Get API keys for the user
    user_keys = db.get_api_keys(user_id)
    
    return {
        "keys": user_keys,
        "count": len(user_keys)
    }

@monetization_blueprint.route('/keys', methods=['POST'])
@jwt_required
@standardize_response
def create_api_key():
    """Create a new API key for the authenticated user"""
    user_id = g.user
    db = get_db_connector()
    
    # Get request data
    data = request.get_json() or {}
    name = data.get('name', 'API Key')
    
    # Generate a new API key
    key_id = str(uuid.uuid4())
    api_key = f"tk_{uuid.uuid4().hex}"
    
    # Store the API key
    key_info = db.create_api_key(key_id, name, user_id, api_key, tier="free")
    
    logger.info(f"Created API key {key_id} for user {user_id}")
    
    # Return the API key info
    return {
        "key_id": key_id,
        "name": name,
        "api_key": api_key,  # Only returned once when created
        "created_at": key_info["created_at"],
        "status": "active",
        "tier": "free"
    }

@monetization_blueprint.route('/keys/<key_id>', methods=['DELETE'])
@jwt_required
@standardize_response
def revoke_api_key(key_id):
    """Revoke an API key"""
    user_id = g.user
    db = get_db_connector()
    
    # Get the key
    key_info = db.get_api_key(key_id)
    
    # Check if the key exists
    if not key_info:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if key_info["user_id"] != user_id:
        return {"error": "You do not have permission to revoke this API key"}, 403
    
    # Revoke the key
    db.update_api_key(key_id, status="revoked")
    
    logger.info(f"Revoked API key {key_id} for user {user_id}")
    
    return {
        "key_id": key_id,
        "status": "revoked",
        "message": "API key revoked successfully"
    }

@monetization_blueprint.route('/keys/<key_id>/tier', methods=['PUT'])
@jwt_required
@standardize_response
def update_key_tier(key_id):
    """Update the subscription tier for an API key"""
    user_id = g.user
    db = get_db_connector()
    
    # Get the key
    key_info = db.get_api_key(key_id)
    
    # Check if the key exists
    if not key_info:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if key_info["user_id"] != user_id:
        return {"error": "You do not have permission to update this API key"}, 403
    
    # Get request data
    data = request.get_json() or {}
    tier = data.get('tier')
    
    # Validate the tier
    if not tier or not db.get_subscription_tier(tier.lower()):
        return {"error": f"Invalid tier: {tier}"}, 400
    
    # Update the tier
    db.update_api_key(key_id, tier=tier.lower())
    
    logger.info(f"Updated tier for API key {key_id} to {tier}")
    
    return {
        "key_id": key_id,
        "tier": tier.lower(),
        "message": "API key tier updated successfully"
    }

@monetization_blueprint.route('/usage')
@jwt_required
@standardize_response
def get_usage():
    """Get API usage for the authenticated user"""
    user_id = g.user
    db = get_db_connector()
    
    # Get usage data for the user
    usage_data = db.get_api_usage(user_id=user_id)
    
    return {
        "usage": usage_data
    }

@monetization_blueprint.route('/usage/<key_id>')
@jwt_required
@standardize_response
def get_key_usage(key_id):
    """Get API usage for a specific API key"""
    user_id = g.user
    db = get_db_connector()
    
    # Get the key
    key_info = db.get_api_key(key_id)
    
    # Check if the key exists
    if not key_info:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if key_info["user_id"] != user_id:
        return {"error": "You do not have permission to view usage for this API key"}, 403
    
    # Get usage data for the key
    usage_data = db.get_api_usage(key_id=key_id)
    
    return {
        "key_id": key_id,
        "name": key_info["name"],
        "tier": key_info["tier"],
        "usage": usage_data
    }

@monetization_blueprint.route('/billing')
@jwt_required
@standardize_response
def get_billing():
    """Get billing information for the authenticated user"""
    user_id = g.user
    db = get_db_connector()
    
    # Get the user's active subscription
    subscription = db.get_user_subscription(user_id)
    
    # Get API keys for the user
    user_keys = db.get_api_keys(user_id)
    active_keys = [key for key in user_keys if key["status"] == "active"]
    
    # Get usage data for the user
    usage_data = db.get_api_usage(user_id=user_id)
    total_requests = sum(day['total_requests'] for day in usage_data)
    
    # Generate a mock billing statement
    billing_data = {
        "current_period": {
            "start": time.strftime("%Y-%m-%d", time.localtime(time.time() - 30 * 86400)),
            "end": time.strftime("%Y-%m-%d", time.localtime(time.time() + 30 * 86400))
        },
        "subscription": {
            "tier": subscription["tier_id"] if subscription else "free",
            "name": subscription["name"] if subscription else "Free Tier",
            "rate_limit": subscription["rate_limit"] if subscription else 60,
            "price": subscription["price"] if subscription else {"amount": 0, "currency": "USD", "interval": "month"},
            "keys": active_keys,
            "total_requests": total_requests
        },
        "invoices": [
            {
                "invoice_id": f"INV-{uuid.uuid4().hex[:8]}",
                "date": time.strftime("%Y-%m-%d", time.localtime(time.time() - 30 * 86400)),
                "amount": subscription["price"]["amount"] if subscription and subscription["price"] else 0,
                "status": "paid"
            },
            {
                "invoice_id": f"INV-{uuid.uuid4().hex[:8]}",
                "date": time.strftime("%Y-%m-%d", time.localtime(time.time())),
                "amount": subscription["price"]["amount"] if subscription and subscription["price"] else 0,
                "status": "pending"
            }
        ]
    }
    
    return billing_data

@monetization_blueprint.route('/track-usage', methods=['POST'])
@roles_required(['admin'])
@standardize_response
def track_usage():
    """
    Track API usage for billing purposes
    This is an internal endpoint for use by the API Gateway
    """
    db = get_db_connector()
    data = request.get_json() or {}
    key_id = data.get('key_id')
    endpoint = data.get('endpoint')
    count = data.get('count', 1)
    date = data.get('date', time.strftime('%Y-%m-%d'))
    
    # Validate the request
    if not key_id or not endpoint:
        return {"error": "Missing required fields: key_id, endpoint"}, 400
    
    # Check if the key exists
    key_info = db.get_api_key(key_id)
    if not key_info:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Track the usage
    success = db.track_api_usage(key_id, endpoint, count, date)
    
    if not success:
        return {"error": "Failed to track API usage"}, 500
    
    logger.debug(f"Tracked {count} requests for key {key_id} to {endpoint} on {date}")
    
    # Get updated count
    usage_data = db.get_api_usage(key_id=key_id)
    endpoint_usage = next(
        (day['endpoints'][0]['requests'] 
         for day in usage_data 
         if day['date'] == date and any(e['endpoint'] == endpoint for e in day['endpoints'])),
        count
    )
    
    return {
        "key_id": key_id,
        "endpoint": endpoint,
        "count": count,
        "date": date,
        "total": endpoint_usage
    }

@monetization_blueprint.route('/test-api-key', methods=['GET'])
@standardize_response
def test_api_key():
    """
    Test endpoint to verify API key validity using mock data
    
    Returns:
        dict: Mock API key validation result with usage information
    """
    logger = logging.getLogger("api_gateway.monetization")
    logger.info("Processing test-api-key request with mock data")
    
    # Get API key from header
    api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        logger.warning("Missing API key in request")
        return {
            "error": "Missing API key",
            "message": "API key is required in the X-API-Key header",
            "help": "Request an API key at /api/monetization/keys or use an existing key"
        }, 401
    
    # Mock data for common test API keys
    mock_keys = {
        "tk_a9a730275279422a90ef243b2d5401fa": {
            "key_id": "22a1b636-abc3-4989-978a-da9afb930add",
            "user_id": "test_user",
            "name": "Test API Key",
            "tier": "basic",
            "status": "active",
            "created_at": 1746383412
        }
    }
    
    # Add a mock key for any valid-looking key format
    if api_key.startswith("tk_") and len(api_key) >= 20:
        # Generate a mock key ID based on the API key
        import hashlib
        key_id = hashlib.md5(api_key.encode()).hexdigest()
        mock_keys[api_key] = {
            "key_id": key_id,
            "user_id": "demo_user",
            "name": "Demo API Key",
            "tier": "free",
            "status": "active",
            "created_at": int(time.time()) - 3600
        }
    
    # Check if API key exists in mock data
    key_info = mock_keys.get(api_key)
    
    if not key_info:
        return {
            "error": "Invalid API key",
            "message": "The provided API key is not valid",
            "help": "Check your API key or request a new one at /api/monetization/keys"
        }, 401
    
    # Mock tier information
    tiers = {
        "free": {
            "tier_id": "free",
            "name": "Free Tier",
            "rate_limit": 60,
            "description": "Basic access for evaluation and personal projects"
        },
        "basic": {
            "tier_id": "basic",
            "name": "Basic Tier",
            "rate_limit": 300,
            "description": "Enhanced access for startups and small businesses"
        },
        "professional": {
            "tier_id": "professional",
            "name": "Professional Tier",
            "rate_limit": 1000,
            "description": "High-volume access for growing businesses"
        }
    }
    
    # Get tier information
    tier_id = key_info.get("tier", "free")
    tier_info = tiers.get(tier_id, tiers["free"])
    
    # Mock usage data
    current_usage = 42  # Mock current usage
    rate_limit = tier_info.get("rate_limit", 60)
    
    # Build response
    return {
        "valid": True,
        "key_info": {
            "key_id": key_info.get("key_id"),
            "user_id": key_info.get("user_id"),
            "name": key_info.get("name"),
            "tier": tier_id,
            "created_at": key_info.get("created_at")
        },
        "tier_info": tier_info,
        "usage": {
            "current": current_usage,
            "remaining": rate_limit - current_usage,
            "reset": "Next billing cycle",
            "period": "Monthly"
        },
        "note": "This is a mock implementation for documentation and testing purposes. In production, actual API usage will be tracked and may affect rate limiting."
    }

@monetization_blueprint.route('/diagnostic', methods=['GET'])
@standardize_response
def diagnostic():
    """
    Simple diagnostic endpoint to verify the API Gateway is functioning
    
    Returns:
        dict: System health information
    """
    logger = logging.getLogger("api_gateway.monetization")
    logger.info("Processing diagnostic request")
    
    # Include system information
    import platform
    import sys
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "api_gateway_version": current_app.config.get('API_GATEWAY_VERSION', "1.0.0")
    }

def register_routes(app):
    """Register monetization routes with the Flask app"""
    app.register_blueprint(monetization_blueprint)
    return app
