"""
Management Endpoints Blueprint
Contains routes for service management, monitoring, and system controls
"""

import logging
import platform
import psutil
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_smorest import Blueprint, abort

# Import schemas
from api.v1.schemas import (
    ModelReloadSchema,
    LogRequestSchema
)

# Create blueprint with API documentation
management_blueprint = Blueprint(
    'management', 
    'management_endpoints',
    description='Service management and monitoring endpoints'
)

# Set up logger
logger = logging.getLogger(__name__)

# Track application start time
start_time = datetime.now()

@management_blueprint.route('/health', methods=['GET'])
@management_blueprint.doc(
    summary="Health check endpoint",
    description="""
    Health check endpoint for monitoring the status and performance of the API service.
    
    Returns detailed health information including:
    - Service status and version
    - System uptime
    - Resource utilization (CPU, memory, disk)
    - AI model configuration
    
    ## Access by Tier
    | Tier | Access Level | Details |
    |------|------------|----------|
    | Basic | Limited | Basic status only |
    | Pro | Standard | Status and resource metrics |
    | Enterprise | Full | Complete system metrics and diagnostics |
    """,
    tags=['Basic Tier']
)
@management_blueprint.response(200, description="Service health information")
@management_blueprint.response(500, description="Service health check failed")
def health_check():
    """
    Health check endpoint for monitoring services
    
    Returns detailed health information about the service
    """
    try:
        # Calculate uptime
        uptime = datetime.now() - start_time
        uptime_seconds = uptime.total_seconds()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # Get system resource usage
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            "status": "healthy",
            "service": current_app.config['APP_NAME'],
            "version": current_app.config['VERSION'],
            "environment": current_app.config['ENV'],
            "uptime": uptime_str,
            "uptime_seconds": int(uptime_seconds),
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_cores": os.cpu_count(),
                "cpu_usage_percent": cpu_usage,
                "memory": {
                    "total_mb": memory.total / (1024 * 1024),
                    "available_mb": memory.available / (1024 * 1024),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024 * 1024 * 1024),
                    "free_gb": disk.free / (1024 * 1024 * 1024),
                    "used_percent": disk.percent
                }
            },
            "ai_service": {
                "default_model": current_app.config['DEFAULT_AI_MODEL'],
                "ollama_url": current_app.config['OLLAMA_BASE_URL'],
                "multimodal_enabled": current_app.config['ENABLE_MULTIMODAL']
            }
        })
    except Exception as e:
        logger.exception(f"Error in health check endpoint: {str(e)}")
        abort(500, message=str(e))

@management_blueprint.route('/models/reload', methods=['POST'])
@management_blueprint.arguments(ModelReloadSchema)
@management_blueprint.doc(
    summary="Reload AI models",
    description="""
    Trigger a reload of AI models without restarting the service.
    
    Can reload specific models by providing a model ID, or reload all models if no ID is specified.
    
    ## Usage Notes
    - Model reloads may cause temporary service interruptions for affected models
    - For large models, reloading may take several minutes
    - This operation requires admin privileges
    
    ## Access by Tier
    | Tier | Access | Models |
    |------|--------|--------|
    | Basic | ❌ No | N/A |
    | Pro | ✓ Limited | Basic models only |
    | Enterprise | ✓ Full | All models |
    """,
    tags=['Enterprise Tier']
)
@management_blueprint.response(200, description="Model reload triggered successfully")
@management_blueprint.response(401, description="Unauthorized - requires admin privileges")
@management_blueprint.response(403, description="Forbidden - requires Enterprise tier")
@management_blueprint.response(500, description="Model reload failed")
def reload_models(reload_data):
    """
    Reload AI models
    
    Allows reloading of AI models without restarting the service
    Supports specific model reloading via JSON payload
    """
    try:
        model_id = reload_data.get('model_id')
        
        if model_id:
            logger.info(f"Reloading specific model: {model_id}")
            # In a real implementation, this would reload the specific model
            message = f"Model {model_id} reload triggered"
        else:
            logger.info("Reloading all models")
            # In a real implementation, this would reload all models
            message = "All models reload triggered"
        
        return jsonify({
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "request_id": request.headers.get('X-Request-ID', 'unknown')
        })
    except Exception as e:
        logger.exception(f"Error reloading models: {str(e)}")
        abort(500, message=str(e))

@management_blueprint.route('/config', methods=['GET'])
@management_blueprint.doc(
    summary="Get service configuration",
    description="""
    Retrieve the current service configuration settings.
    
    Returns non-sensitive configuration values appropriate for the user's tier:
    - Basic: Limited configuration visibility
    - Pro: Standard configuration options
    - Enterprise: Complete configuration details
    
    Sensitive values like API keys and secrets are always excluded.
    """,
    tags=['Pro Tier']
)
@management_blueprint.response(200, description="Configuration retrieved successfully")
@management_blueprint.response(401, description="Unauthorized")
@management_blueprint.response(403, description="Forbidden - requires Pro tier or higher")
def get_config():
    """
    Get current service configuration
    
    Returns non-sensitive configuration values
    """
    try:
        # Filter out sensitive configuration values
        safe_config = {
            "app_name": current_app.config['APP_NAME'],
            "version": current_app.config['VERSION'],
            "environment": current_app.config['ENV'],
            "default_model": current_app.config['DEFAULT_AI_MODEL'],
            "ollama_base_url": current_app.config['OLLAMA_BASE_URL'],
            "default_max_tokens": current_app.config['DEFAULT_MAX_TOKENS'],
            "default_temperature": current_app.config['DEFAULT_TEMPERATURE'],
            "langchain_cache": current_app.config['LANGCHAIN_CACHE'],
            "langchain_debug": current_app.config['LANGCHAIN_VERBOSE'],  # Renamed for clarity
            "cors_origins": current_app.config['CORS_ORIGINS'],
            "enable_multimodal": current_app.config['ENABLE_MULTIMODAL'],
            "log_level": current_app.config['LOG_LEVEL'],
            # Exclude secret key and other sensitive values
        }
        
        return jsonify(safe_config)
    except Exception as e:
        logger.exception(f"Error retrieving configuration: {str(e)}")
        abort(500, message=str(e))

@management_blueprint.route('/logs', methods=['GET'])
@management_blueprint.doc(
    summary="Retrieve application logs",
    description="""
    Get recent application logs with filtering options.
    
    ## Query Parameters
    - `lines`: Number of log lines to return (default: 100, max: 1000)
    - `level`: Minimum log level (default: INFO)
    - `service`: Filter by service component
    
    ## Access by Tier
    | Tier | Access | Log Retention |
    |------|--------|---------------|
    | Basic | ❌ No | N/A |
    | Pro | ✓ Limited | 7 days |
    | Enterprise | ✓ Full | 90 days |
    
    ## Sample Response
    ```json
    {
      "logs": [
        {
          "timestamp": "2025-05-03T12:00:00",
          "level": "INFO",
          "service": "api",
          "message": "Request processed successfully"
        }
      ],
      "count": 1
    }
    ```
    """,
    tags=['Enterprise Tier']
)
@management_blueprint.response(200, description="Logs retrieved successfully")
@management_blueprint.response(401, description="Unauthorized")
@management_blueprint.response(403, description="Forbidden - requires Enterprise tier")
def get_logs():
    """
    Get recent application logs
    
    Query parameters:
    - lines: Number of log lines to return (default: 100, max: 1000)
    - level: Minimum log level (default: INFO)
    - service: Filter by service component
    
    Returns recent log entries
    """
    try:
        # This is a placeholder - a real implementation would retrieve logs
        # from a log storage system or file
        
        lines = min(int(request.args.get('lines', 100)), 1000)
        level = request.args.get('level', 'INFO')
        service = request.args.get('service')
        
        # Mock response for demonstration
        mock_logs = []
        for i in range(lines):
            timestamp = (datetime.now() - timedelta(minutes=i)).isoformat()
            mock_logs.append({
                "timestamp": timestamp,
                "level": level,
                "service": service or "api",
                "message": f"Sample log entry {i+1}"
            })
        
        return jsonify({
            "logs": mock_logs,
            "count": len(mock_logs)
        })
    except Exception as e:
        logger.exception(f"Error retrieving logs: {str(e)}")
        abort(500, message=str(e))

@management_blueprint.route('/usage', methods=['GET'])
@management_blueprint.doc(
    summary="API usage and billing information",
    description="""
    Get usage statistics and billing information for the current billing period.
    
    ## Return Data Includes:
    - Current billing period information
    - API calls made by endpoint and tier
    - Usage-based costs for the period
    - Rate limiting status
    
    ## Access by Tier
    | Tier | Usage Data | Cost Tracking | Retention |
    |------|------------|---------------|-----------|
    | Basic | Current month | Basic | 1 month |
    | Pro | 6 months | Standard | 12 months |
    | Enterprise | 24 months | Detailed | 36 months |
    
    This endpoint is critical for usage-based billing and consumption tracking.
    """,
    tags=['Basic Tier']
)
@management_blueprint.response(200, description="Usage data retrieved successfully")
@management_blueprint.response(401, description="Unauthorized")
def get_usage():
    """Get API usage statistics and billing information"""
    try:
        # This is a placeholder - a real implementation would query a billing database
        
        current_month = datetime.now().strftime("%B %Y")
        
        # Sample usage data
        usage_data = {
            "billing_period": {
                "start": f"{datetime.now().replace(day=1).strftime('%Y-%m-%d')}",
                "end": f"{datetime.now().strftime('%Y-%m-%d')}",
                "status": "active"
            },
            "usage": {
                "ai": {
                    "analyze": {"count": 145, "cost": 1.45},
                    "chat": {"count": 320, "cost": 1.60},
                    "completion": {"count": 78, "cost": 0.78}
                },
                "multimodal": {
                    "image": {"count": 52, "cost": 1.04},
                    "audio": {"count": 8, "cost": 0.40},
                    "video": {"count": 3, "cost": 0.30}
                }
            },
            "total_cost": 5.57,
            "subscription_tier": "basic",
            "rate_limits": {
                "current_usage": 78,
                "limit_per_minute": 100,
                "reset_in_seconds": 42
            }
        }
        
        return jsonify(usage_data)
    except Exception as e:
        logger.exception(f"Error retrieving usage data: {str(e)}")
        abort(500, message=str(e))

@management_blueprint.route('/documentation', methods=['GET'])
@management_blueprint.doc(
    summary="API Documentation Information",
    description="""
    Retrieve information about available API documentation resources.
    
    This endpoint provides links to various documentation resources targeted at 
    different developer experience levels:
    
    - Beginner guides and tutorials
    - Intermediate examples and quick-start guides
    - Advanced API references and integration patterns
    
    Documentation includes interactive examples, code snippets, and 
    comprehensive walkthroughs.
    """,
    tags=['Basic Tier']
)
@management_blueprint.response(200, description="Documentation information retrieved")
def get_documentation():
    """Get API documentation information"""
    return jsonify({
        "documentation_resources": {
            "beginner_resources": {
                "getting_started": "/docs/getting-started",
                "tutorials": "/docs/tutorials",
                "video_guides": "/docs/videos",
                "interactive_examples": "/docs/examples/interactive"
            },
            "intermediate_resources": {
                "code_snippets": "/docs/code-snippets",
                "implementation_patterns": "/docs/patterns",
                "use_cases": "/docs/use-cases",
                "troubleshooting": "/docs/troubleshooting"
            },
            "advanced_resources": {
                "api_reference": "/docs/api",
                "architecture_guides": "/docs/architecture",
                "best_practices": "/docs/best-practices",
                "integration_guides": "/docs/integrations"
            }
        },
        "support_resources": {
            "community_forums": "https://community.techsaas.example.com",
            "github": "https://github.com/techsaas/api-docs",
            "support_email": "support@techsaas.example.com",
            "status_page": "https://status.techsaas.example.com"
        },
        "interactive_documentation": {
            "swagger_ui": "/api/docs",
            "redoc": "/api/redoc",
            "postman_collection": "/api/postman.json"
        }
    })
