"""
Subscription Management Endpoints Blueprint
Contains routes for managing API keys, subscription tiers, and usage tracking
"""

import logging
import uuid
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_smorest import Blueprint, abort

# Import schemas
from api.v1.schemas import (
    APIKeySchema,
    UsageQuerySchema
)

# Create blueprint with API documentation
subscription_blueprint = Blueprint(
    'subscription', 
    'subscription_endpoints',
    description='Subscription and API key management endpoints'
)

# Set up logger
logger = logging.getLogger(__name__)

# In-memory storage for API keys (replace with database in production)
api_keys = {}

@subscription_blueprint.route('/keys', methods=['GET'])
@subscription_blueprint.doc(
    summary="List API keys",
    description="""
    Retrieve a list of API keys associated with the current account.
    
    Returns key metadata including:
    - Key name and identifier (partial)
    - Creation and expiration dates
    - Associated tier and permissions
    - Usage statistics
    
    API keys are critical for monetization as they determine tier access and track usage.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(200, description="API keys retrieved successfully")
@subscription_blueprint.response(401, description="Unauthorized")
def list_api_keys():
    """List all API keys for the current user"""
    # This would normally get keys from a database
    # For now, just return sample data
    
    current_user_id = "user-1234"  # This would come from authentication
    user_keys = [k for k in api_keys.values() if k.get('user_id') == current_user_id]
    
    # Obscure actual keys in the response
    sanitized_keys = []
    for key in user_keys:
        sanitized_keys.append({
            "id": key["id"],
            "name": key["name"],
            "prefix": key["key"][:8] + "...",
            "created_at": key["created_at"],
            "expires_at": key["expires_at"],
            "tier": key["tier"],
            "permissions": key["permissions"],
            "last_used": key.get("last_used")
        })
    
    return jsonify({
        "api_keys": sanitized_keys if sanitized_keys else [],
        "count": len(sanitized_keys),
        "max_keys": current_app.config.get('MAX_API_KEYS_PER_USER', 5)
    })

@subscription_blueprint.route('/keys', methods=['POST'])
@subscription_blueprint.arguments(APIKeySchema)
@subscription_blueprint.doc(
    summary="Create new API key",
    description="""
    Generate a new API key for accessing the service.
    
    ## Key Configuration Options
    - Name (required): Friendly name for the key
    - Expiration (optional): When the key should expire
    - Tier (optional): Which subscription tier to associate (default: user's current tier)
    - Permissions (optional): Specific feature permissions for this key
    
    ## Security Notice
    The full API key is only shown once upon creation and cannot be retrieved again.
    Store it securely.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(201, description="API key created successfully")
@subscription_blueprint.response(400, description="Invalid request parameters")
@subscription_blueprint.response(401, description="Unauthorized")
@subscription_blueprint.response(403, description="Maximum number of API keys reached")
def create_api_key(key_data):
    """Create a new API key"""
    current_user_id = "user-1234"  # This would come from authentication
    user_keys = [k for k in api_keys.values() if k.get('user_id') == current_user_id]
    
    # Check if max keys reached
    max_keys = current_app.config.get('MAX_API_KEYS_PER_USER', 5)
    if len(user_keys) >= max_keys:
        abort(403, message=f"Maximum number of API keys reached ({max_keys})")
    
    # Generate a new API key
    api_key_value = f"ts_{uuid.uuid4().hex}_{uuid.uuid4().hex}"
    key_id = str(uuid.uuid4())
    
    # Set expiration (default to 1 year if not specified)
    expires_at = None
    if key_data.get('expiration'):
        expires_at = key_data.get('expiration').isoformat()
    else:
        expires_at = (datetime.now() + timedelta(days=365)).isoformat()
    
    # Create the key record
    api_key_record = {
        "id": key_id,
        "key": api_key_value,
        "name": key_data.get('name'),
        "user_id": current_user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "tier": key_data.get('tier', 'basic'),
        "permissions": key_data.get('permissions', ['read']),
        "last_used": None
    }
    
    # Store the key
    api_keys[key_id] = api_key_record
    
    logger.info(f"Created new API key: {key_id} for user {current_user_id}")
    
    # Return the full key (only time it's ever returned)
    return jsonify({
        "api_key": api_key_value,
        "id": key_id,
        "name": api_key_record["name"],
        "expires_at": api_key_record["expires_at"],
        "tier": api_key_record["tier"],
        "permissions": api_key_record["permissions"],
        "message": "Store this API key securely. It will not be shown again."
    }), 201

@subscription_blueprint.route('/keys/<key_id>', methods=['DELETE'])
@subscription_blueprint.doc(
    summary="Revoke API key",
    description="""
    Revoke an API key to immediately prevent all further access.
    
    This operation is irreversible - once revoked, the key cannot be restored.
    Any services using this key will need to be updated with a new key.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(200, description="API key revoked successfully")
@subscription_blueprint.response(401, description="Unauthorized")
@subscription_blueprint.response(403, description="Forbidden - not your API key")
@subscription_blueprint.response(404, description="API key not found")
def revoke_api_key(key_id):
    """Revoke an API key"""
    if key_id not in api_keys:
        abort(404, message="API key not found")
    
    current_user_id = "user-1234"  # This would come from authentication
    
    # Check if the key belongs to this user
    if api_keys[key_id]['user_id'] != current_user_id:
        abort(403, message="You do not have permission to revoke this key")
    
    # Revoke the key by deleting it
    key_name = api_keys[key_id]['name']
    del api_keys[key_id]
    
    logger.info(f"Revoked API key {key_id} ({key_name}) for user {current_user_id}")
    
    return jsonify({
        "message": f"API key '{key_name}' has been revoked",
        "revoked_at": datetime.now().isoformat()
    })

@subscription_blueprint.route('/usage/current', methods=['GET'])
@subscription_blueprint.doc(
    summary="Get current billing period usage",
    description="""
    Retrieve detailed API usage for the current billing period.
    
    Usage data includes:
    - API calls by endpoint category
    - Quota usage and limits
    - Estimated billing amount
    - Rate limiting status
    
    The current billing period is the ongoing month, starting from the 1st.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(200, description="Usage data retrieved")
@subscription_blueprint.response(401, description="Unauthorized")
def get_current_usage():
    """Get usage data for the current billing period"""
    # This would normally query a usage tracking database
    # For now, just return mock data
    
    current_time = datetime.now()
    start_of_month = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = 30  # Simplified
    days_elapsed = (current_time - start_of_month).days + 1
    
    # Mock usage data
    usage_data = {
        "billing_period": {
            "start": start_of_month.isoformat(),
            "end": current_time.isoformat(),
            "days_elapsed": days_elapsed,
            "days_in_period": days_in_month,
            "percent_elapsed": round((days_elapsed / days_in_month) * 100, 1)
        },
        "usage": {
            "ai": {
                "analyze": {"count": 145, "quota": 5000, "cost": 1.45},
                "chat": {"count": 320, "quota": 10000, "cost": 1.60},
                "completion": {"count": 78, "quota": 2000, "cost": 0.78}
            },
            "multimodal": {
                "image": {"count": 52, "quota": 500, "cost": 1.04},
                "audio": {"count": 8, "quota": 100, "cost": 0.40},
                "video": {"count": 3, "quota": 50, "cost": 0.30}
            }
        },
        "total_usage": 606,
        "total_quota": 17650,
        "quota_percent_used": round((606 / 17650) * 100, 1),
        "total_cost": 5.57,
        "subscription": {
            "tier": "basic",
            "monthly_base_fee": 9.99,
            "estimated_total": 15.56,  # Base fee + usage
        }
    }
    
    return jsonify(usage_data)

@subscription_blueprint.route('/plans', methods=['GET'])
@subscription_blueprint.doc(
    summary="List available subscription plans",
    description="""
    Get information about all available subscription plans and pricing.
    
    Returns detailed plan information including:
    - Monthly base prices
    - Included API quotas
    - Rate limits
    - Feature availability
    - Overage pricing
    
    Use this information to compare plans and choose the best option.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(200, description="Subscription plans retrieved")
def list_subscription_plans():
    """List all available subscription plans"""
    plans = [
        {
            "id": "basic",
            "name": "Basic Plan",
            "description": "Perfect for hobbyists and small projects",
            "monthly_price": 9.99,
            "features": {
                "ai": {
                    "analyze": True,
                    "chat": True,
                    "completion": False
                },
                "multimodal": {
                    "image": True,
                    "audio": False,
                    "video": False
                }
            },
            "quotas": {
                "ai_analyze": 5000,
                "ai_chat": 10000,
                "multimodal_image": 500
            },
            "rate_limits": {
                "requests_per_minute": 100,
                "requests_per_day": 10000
            },
            "pricing_overage": {
                "ai_analyze": 0.01,
                "ai_chat": 0.005,
                "multimodal_image": 0.02
            }
        },
        {
            "id": "pro",
            "name": "Professional Plan",
            "description": "For professional developers and small teams",
            "monthly_price": 49.99,
            "features": {
                "ai": {
                    "analyze": True,
                    "chat": True,
                    "completion": True
                },
                "multimodal": {
                    "image": True,
                    "audio": True,
                    "video": False
                }
            },
            "quotas": {
                "ai_analyze": 50000,
                "ai_chat": 100000,
                "ai_completion": 25000,
                "multimodal_image": 5000,
                "multimodal_audio": 1000
            },
            "rate_limits": {
                "requests_per_minute": 500,
                "requests_per_day": 100000
            },
            "pricing_overage": {
                "ai_analyze": 0.005,
                "ai_chat": 0.003,
                "ai_completion": 0.008,
                "multimodal_image": 0.015,
                "multimodal_audio": 0.05
            }
        },
        {
            "id": "enterprise",
            "name": "Enterprise Plan",
            "description": "For large-scale applications and businesses",
            "monthly_price": 499.99,
            "features": {
                "ai": {
                    "analyze": True,
                    "chat": True,
                    "completion": True
                },
                "multimodal": {
                    "image": True,
                    "audio": True,
                    "video": True
                }
            },
            "quotas": {
                "ai_analyze": "Unlimited",
                "ai_chat": "Unlimited",
                "ai_completion": "Unlimited",
                "multimodal_image": "Unlimited",
                "multimodal_audio": "Unlimited",
                "multimodal_video": "Unlimited"
            },
            "rate_limits": {
                "requests_per_minute": 2000,
                "requests_per_day": "Unlimited"
            },
            "pricing_overage": {
                "ai_analyze": 0.002,
                "ai_chat": 0.001,
                "ai_completion": 0.005,
                "multimodal_image": 0.01,
                "multimodal_audio": 0.03,
                "multimodal_video": 0.10
            }
        }
    ]
    
    return jsonify({
        "plans": plans,
        "current_plan": "basic"  # Would be the user's actual plan
    })

@subscription_blueprint.route('/plans/upgrade', methods=['POST'])
@subscription_blueprint.doc(
    summary="Upgrade subscription plan",
    description="""
    Upgrade the current subscription to a higher tier.
    
    This endpoint initiates the upgrade process, which may require additional payment information
    depending on the selected plan. The upgrade takes effect immediately upon successful payment.
    
    Unused quota from the previous plan will be prorated and credited to the new plan.
    """,
    tags=['Basic Tier']
)
@subscription_blueprint.response(200, description="Subscription upgrade initiated")
@subscription_blueprint.response(400, description="Invalid request parameters")
@subscription_blueprint.response(401, description="Unauthorized")
@subscription_blueprint.response(402, description="Payment required")
def upgrade_plan():
    """Upgrade to a higher subscription plan"""
    data = request.json or {}
    
    if 'plan_id' not in data:
        abort(400, message="plan_id is required")
    
    plan_id = data.get('plan_id')
    valid_plans = ['basic', 'pro', 'enterprise']
    
    if plan_id not in valid_plans:
        abort(400, message=f"Invalid plan_id. Must be one of: {', '.join(valid_plans)}")
    
    # Mock response - this would normally initiate a payment flow
    return jsonify({
        "success": True,
        "message": f"Upgrade to {plan_id} plan initiated",
        "next_steps": "Complete payment to activate your new plan",
        "payment_url": "/api/v1/subscription/payment/checkout?plan=" + plan_id,
        "effective_date": datetime.now().isoformat()
    })
