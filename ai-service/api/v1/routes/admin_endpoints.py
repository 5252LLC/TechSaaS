"""
Admin Endpoints Blueprint
Contains secure routes for administrative functions
"""

import logging
import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from flask_smorest import Blueprint, abort

# Import middleware
from api.v1.middleware import require_admin, admin_only

# Create blueprint
admin_blueprint = Blueprint(
    'admin', 
    'admin_endpoints',
    description='Administrative endpoints for platform management'
)

# Set up logger
logger = logging.getLogger(__name__)

@admin_blueprint.route('/status', methods=['GET'])
@require_admin
def admin_status():
    """Get detailed admin status information"""
    try:
        # Get memory usage and other system info
        # This would normally access much more detailed information
        status = {
            "timestamp": datetime.now().isoformat(),
            "admin_access": True,
            "environment": current_app.config['ENV'],
            "config_loaded": True,
            "api_version": current_app.config['VERSION'],
            "server_time": datetime.now().isoformat(),
            "auth_mode": "Disabled for Development" if current_app.config.get('DISABLE_AUTH_FOR_DEV') else "Enforced"
        }
        
        return jsonify(status)
    except Exception as e:
        logger.exception(f"Error in admin status endpoint: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/config', methods=['GET'])
@require_admin
def get_admin_config():
    """Get full configuration including sensitive values (admin only)"""
    try:
        # Get all configuration (excluding certain sensitive items)
        # In a real app, we'd filter out some values like raw encryption keys
        config = {k: v for k, v in current_app.config.items() 
                 if not k.startswith('_') and k != 'SECRET_KEY'}
        
        return jsonify({
            "config": config,
            "environment": current_app.config['ENV'],
            "message": "This endpoint exposes configuration for admin use only"
        })
    except Exception as e:
        logger.exception(f"Error retrieving admin config: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/users', methods=['GET'])
@require_admin
def list_users():
    """List all users with their subscription information"""
    try:
        # This would normally query a database
        # Mock data for demonstration
        users = [
            {
                "id": "user-1234",
                "email": "user@example.com",
                "name": "Test User",
                "subscription": {
                    "tier": "basic",
                    "status": "active",
                    "start_date": "2025-01-01",
                    "next_billing": "2025-06-01"
                },
                "api_keys": 3,
                "usage": {
                    "current_month": 352,
                    "quota_used_percent": 7
                }
            },
            {
                "id": "user-5678",
                "email": "premium@example.com",
                "name": "Premium User",
                "subscription": {
                    "tier": "pro",
                    "status": "active",
                    "start_date": "2025-02-15",
                    "next_billing": "2025-05-15"
                },
                "api_keys": 5,
                "usage": {
                    "current_month": 4325,
                    "quota_used_percent": 43
                }
            }
        ]
        
        return jsonify({
            "users": users,
            "count": len(users),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.exception(f"Error listing users: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/models', methods=['GET'])
@require_admin
def list_models():
    """List all available and configured AI models"""
    try:
        # This would normally query the available models from various providers
        models = {
            "internal": [
                {
                    "id": "ollama/llama2",
                    "name": "Llama 2",
                    "type": "text",
                    "status": "active",
                    "tiers": ["basic", "pro", "enterprise"]
                },
                {
                    "id": "ollama/mistral",
                    "name": "Mistral",
                    "type": "text",
                    "status": "active",
                    "tiers": ["basic", "pro", "enterprise"]
                },
                {
                    "id": "ollama/codellama",
                    "name": "Code Llama",
                    "type": "code",
                    "status": "active",
                    "tiers": ["pro", "enterprise"]
                },
                {
                    "id": "ollama/llava",
                    "name": "LLaVa",
                    "type": "multimodal",
                    "status": "active",
                    "tiers": ["pro", "enterprise"]
                }
            ],
            "external_connectors": [
                {
                    "id": "openai/gpt-4",
                    "name": "OpenAI GPT-4",
                    "type": "text",
                    "status": "available",
                    "tiers": ["enterprise"]
                },
                {
                    "id": "anthropic/claude-3",
                    "name": "Anthropic Claude 3",
                    "type": "text",
                    "status": "available",
                    "tiers": ["enterprise"]
                }
            ],
            "custom": []  # Customer-specific custom models would go here
        }
        
        return jsonify(models)
    except Exception as e:
        logger.exception(f"Error listing models: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/usage/stats', methods=['GET'])
@require_admin
def usage_stats():
    """Get platform-wide usage statistics"""
    try:
        # This would normally query a usage tracking database
        # Mock data for demonstration
        
        # Get time period from query params
        period = request.args.get('period', 'day')  # day, week, month, year
        
        stats = {
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "api_calls": {
                "total": 15243,
                "by_endpoint": {
                    "ai/analyze": 5432,
                    "ai/chat": 7891,
                    "ai/completion": 1234,
                    "multimodal/analyze": 686
                },
                "by_tier": {
                    "basic": 7621,
                    "pro": 6018,
                    "enterprise": 1604
                }
            },
            "models_used": {
                "ollama/llama2": 8734,
                "ollama/mistral": 3567,
                "ollama/codellama": 1892,
                "ollama/llava": 686,
                "openai/gpt-4": 364
            },
            "compute_resources": {
                "cpu_hours": 187.3,
                "gpu_hours": 43.6,
                "average_response_time_ms": 750
            }
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.exception(f"Error getting usage statistics: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/security/logs', methods=['GET'])
@require_admin
def security_logs():
    """View security-related logs and alerts"""
    try:
        # This would normally query security logs
        # Mock data for demonstration
        
        # Get parameters
        limit = min(int(request.args.get('limit', 20)), 100)
        level = request.args.get('level', 'all')  # info, warning, alert, all
        
        logs = [
            {
                "timestamp": (datetime.now().isoformat()),
                "level": "alert",
                "type": "authentication_failure",
                "message": "Multiple failed admin login attempts",
                "ip": "192.168.1.123",
                "details": {
                    "attempts": 5,
                    "timespan_seconds": 60
                }
            },
            {
                "timestamp": (datetime.now().isoformat()),
                "level": "warning",
                "type": "rate_limit_exceeded",
                "message": "Rate limit exceeded for API key",
                "user_id": "user-5678",
                "details": {
                    "endpoint": "/api/v1/ai/completion",
                    "requests": 520,
                    "limit": 500
                }
            },
            {
                "timestamp": (datetime.now().isoformat()),
                "level": "info",
                "type": "new_api_key",
                "message": "New API key created",
                "user_id": "user-1234"
            }
        ]
        
        # Filter by level if requested
        if level != 'all':
            logs = [log for log in logs if log['level'] == level]
        
        return jsonify({
            "logs": logs[:limit],
            "count": len(logs[:limit]),
            "total_count": len(logs)
        })
    except Exception as e:
        logger.exception(f"Error retrieving security logs: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/connectors', methods=['GET'])
@require_admin
def list_connectors():
    """List all API connectors and their configurations"""
    try:
        # This would normally query the database for connector configurations
        # Mock data for demonstration
        connectors = [
            {
                "id": "openai-connector",
                "provider": "openai",
                "status": "active",
                "models_available": ["gpt-3.5-turbo", "gpt-4"],
                "security": {
                    "content_filtering": True,
                    "prompt_injection_protection": True,
                    "request_sandboxing": True
                },
                "usage": {
                    "daily_requests": 364,
                    "monthly_cost": 218.45
                }
            },
            {
                "id": "anthropic-connector",
                "provider": "anthropic",
                "status": "active",
                "models_available": ["claude-2", "claude-3"],
                "security": {
                    "content_filtering": True,
                    "prompt_injection_protection": True,
                    "request_sandboxing": True
                },
                "usage": {
                    "daily_requests": 126,
                    "monthly_cost": 89.23
                }
            }
        ]
        
        return jsonify({
            "connectors": connectors,
            "count": len(connectors),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.exception(f"Error listing API connectors: {str(e)}")
        abort(500, message=str(e))

@admin_blueprint.route('/test-auth-override', methods=['GET'])
def test_auth_override():
    """
    Test endpoint to check if auth override is working.
    This endpoint doesn't require admin authentication if DISABLE_AUTH_FOR_DEV is true.
    """
    if current_app.config.get('DISABLE_AUTH_FOR_DEV', False):
        return jsonify({
            "status": "success",
            "message": "Auth override is working - you can use the API without authentication in development mode",
            "auth_disabled": True,
            "environment": current_app.config['ENV']
        })
    else:
        return jsonify({
            "status": "notice",
            "message": "Auth override is disabled - you need to authenticate for API access",
            "auth_disabled": False,
            "environment": current_app.config['ENV']
        }), 401
