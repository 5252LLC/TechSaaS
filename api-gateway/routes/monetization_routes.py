"""
API Monetization Routes

This module provides routes for API monetization, including API key management,
subscription tiers, and usage tracking.
"""

import time
import logging
import uuid
from flask import Blueprint, jsonify, request, g, current_app
from middleware.security import jwt_required, roles_required
from middleware.response_transform import standardize_response

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

# In a real implementation, these would be stored in a database
# For now, we'll use in-memory data for demonstration
API_KEYS = {}
API_USAGE = {}

@monetization_blueprint.route('/tiers')
@standardize_response
def list_tiers():
    """List available subscription tiers"""
    return {
        "tiers": list(SUBSCRIPTION_TIERS.values()),
        "count": len(SUBSCRIPTION_TIERS)
    }

@monetization_blueprint.route('/tier/<tier_id>')
@standardize_response
def get_tier(tier_id):
    """Get details for a specific tier"""
    tier = SUBSCRIPTION_TIERS.get(tier_id.lower())
    if not tier:
        return {"error": f"Unknown tier: {tier_id}"}, 404
    
    return {"tier": tier}

@monetization_blueprint.route('/keys', methods=['GET'])
@jwt_required
@standardize_response
def list_api_keys():
    """List API keys for the authenticated user"""
    user_id = g.user
    
    # Get API keys for the user
    user_keys = [
        {
            "key_id": key_id,
            "name": key_info["name"],
            "created_at": key_info["created_at"],
            "last_used": key_info.get("last_used"),
            "status": key_info["status"]
        }
        for key_id, key_info in API_KEYS.items()
        if key_info["user_id"] == user_id
    ]
    
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
    
    # Get request data
    data = request.get_json() or {}
    name = data.get('name', 'API Key')
    
    # Generate a new API key
    key_id = str(uuid.uuid4())
    api_key = f"tk_{uuid.uuid4().hex}"
    
    # Store the API key info
    API_KEYS[key_id] = {
        "name": name,
        "user_id": user_id,
        "key": api_key,
        "created_at": time.time(),
        "status": "active",
        "tier": "free"  # Default tier for new keys
    }
    
    logger.info(f"Created API key {key_id} for user {user_id}")
    
    # Return the API key info
    return {
        "key_id": key_id,
        "name": name,
        "api_key": api_key,  # Only returned once when created
        "created_at": API_KEYS[key_id]["created_at"],
        "status": "active",
        "tier": "free"
    }

@monetization_blueprint.route('/keys/<key_id>', methods=['DELETE'])
@jwt_required
@standardize_response
def revoke_api_key(key_id):
    """Revoke an API key"""
    user_id = g.user
    
    # Check if the key exists
    if key_id not in API_KEYS:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if API_KEYS[key_id]["user_id"] != user_id:
        return {"error": "You do not have permission to revoke this API key"}, 403
    
    # Revoke the key
    API_KEYS[key_id]["status"] = "revoked"
    
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
    
    # Check if the key exists
    if key_id not in API_KEYS:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if API_KEYS[key_id]["user_id"] != user_id:
        return {"error": "You do not have permission to update this API key"}, 403
    
    # Get request data
    data = request.get_json() or {}
    tier = data.get('tier')
    
    # Validate the tier
    if not tier or tier.lower() not in SUBSCRIPTION_TIERS:
        return {"error": f"Invalid tier: {tier}"}, 400
    
    # Update the tier
    API_KEYS[key_id]["tier"] = tier.lower()
    
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
    
    # Get API keys for the user
    user_keys = [
        key_id for key_id, key_info in API_KEYS.items()
        if key_info["user_id"] == user_id
    ]
    
    # Aggregate usage for the user's keys
    usage = {}
    for key_id in user_keys:
        key_usage = API_USAGE.get(key_id, {})
        
        # Aggregate daily usage
        for day, day_usage in key_usage.items():
            if day not in usage:
                usage[day] = {}
            
            # Aggregate endpoint usage
            for endpoint, count in day_usage.items():
                usage[day][endpoint] = usage[day].get(endpoint, 0) + count
    
    # Format the response
    usage_data = []
    for day, day_usage in usage.items():
        day_data = {
            "date": day,
            "total_requests": sum(day_usage.values()),
            "endpoints": [
                {
                    "endpoint": endpoint,
                    "requests": count
                }
                for endpoint, count in day_usage.items()
            ]
        }
        usage_data.append(day_data)
    
    # Sort by date, newest first
    usage_data.sort(key=lambda x: x["date"], reverse=True)
    
    return {
        "usage": usage_data
    }

@monetization_blueprint.route('/usage/<key_id>')
@jwt_required
@standardize_response
def get_key_usage(key_id):
    """Get API usage for a specific API key"""
    user_id = g.user
    
    # Check if the key exists
    if key_id not in API_KEYS:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Check if the key belongs to the user
    if API_KEYS[key_id]["user_id"] != user_id:
        return {"error": "You do not have permission to view usage for this API key"}, 403
    
    # Get usage for the key
    key_usage = API_USAGE.get(key_id, {})
    
    # Format the response
    usage_data = []
    for day, day_usage in key_usage.items():
        day_data = {
            "date": day,
            "total_requests": sum(day_usage.values()),
            "endpoints": [
                {
                    "endpoint": endpoint,
                    "requests": count
                }
                for endpoint, count in day_usage.items()
            ]
        }
        usage_data.append(day_data)
    
    # Sort by date, newest first
    usage_data.sort(key=lambda x: x["date"], reverse=True)
    
    return {
        "key_id": key_id,
        "name": API_KEYS[key_id]["name"],
        "tier": API_KEYS[key_id]["tier"],
        "usage": usage_data
    }

@monetization_blueprint.route('/billing')
@jwt_required
@standardize_response
def get_billing():
    """Get billing information for the authenticated user"""
    user_id = g.user
    
    # Get API keys for the user
    user_keys = [
        key_id for key_id, key_info in API_KEYS.items()
        if key_info["user_id"] == user_id and key_info["status"] == "active"
    ]
    
    # Get current tier for each key
    key_tiers = {
        key_id: API_KEYS[key_id]["tier"]
        for key_id in user_keys
    }
    
    # Calculate total usage
    total_requests = 0
    for key_id in user_keys:
        key_usage = API_USAGE.get(key_id, {})
        for day, day_usage in key_usage.items():
            total_requests += sum(day_usage.values())
    
    # Generate a mock billing statement
    billing_data = {
        "current_period": {
            "start": "2025-05-01",
            "end": "2025-05-31"
        },
        "subscription": {
            "keys": [
                {
                    "key_id": key_id,
                    "name": API_KEYS[key_id]["name"],
                    "tier": key_tiers[key_id],
                    "base_price": SUBSCRIPTION_TIERS[key_tiers[key_id]]["price"]["amount"],
                    "usage": API_USAGE.get(key_id, {})
                }
                for key_id in user_keys
            ],
            "total_requests": total_requests
        },
        "invoices": [
            {
                "invoice_id": "INV-001",
                "date": "2025-04-01",
                "amount": 49.00,
                "status": "paid"
            },
            {
                "invoice_id": "INV-002",
                "date": "2025-05-01",
                "amount": 49.00,
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
    data = request.get_json() or {}
    key_id = data.get('key_id')
    endpoint = data.get('endpoint')
    count = data.get('count', 1)
    date = data.get('date', time.strftime('%Y-%m-%d'))
    
    # Validate the request
    if not key_id or not endpoint:
        return {"error": "Missing required fields: key_id, endpoint"}, 400
    
    # Check if the key exists
    if key_id not in API_KEYS:
        return {"error": f"Unknown API key: {key_id}"}, 404
    
    # Initialize usage tracking for the key
    if key_id not in API_USAGE:
        API_USAGE[key_id] = {}
    
    # Initialize usage tracking for the date
    if date not in API_USAGE[key_id]:
        API_USAGE[key_id][date] = {}
    
    # Track the usage
    API_USAGE[key_id][date][endpoint] = API_USAGE[key_id][date].get(endpoint, 0) + count
    
    logger.debug(f"Tracked {count} requests for key {key_id} to {endpoint} on {date}")
    
    return {
        "key_id": key_id,
        "endpoint": endpoint,
        "count": count,
        "date": date,
        "total": API_USAGE[key_id][date][endpoint]
    }

def register_routes(app):
    """Register monetization routes with the Flask app"""
    app.register_blueprint(monetization_blueprint)
    return app
