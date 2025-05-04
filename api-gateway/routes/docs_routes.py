"""
API Documentation Routes

This module provides routes for API documentation, including Swagger UI,
ReDoc, and OpenAPI specification endpoints.
"""

import os
import json
import logging
from flask import Blueprint, jsonify, render_template, send_from_directory, current_app

logger = logging.getLogger("api_gateway.docs")

# Create blueprint
docs_blueprint = Blueprint('docs', __name__, url_prefix='/api/docs')

# Path to the static files for Swagger UI and ReDoc
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'docs')

def generate_openapi_spec():
    """
    Generate the OpenAPI specification for the API Gateway
    
    Returns:
        dict: OpenAPI specification
    """
    from services.service_discovery import get_registry
    
    registry = get_registry()
    
    # Base OpenAPI specification
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "TechSaaS API Gateway",
            "description": "API Gateway for the TechSaaS Platform",
            "version": current_app.config.get('API_VERSION', 'v1'),
            "contact": {
                "name": "TechSaaS Support",
                "email": "525277x@gmail.com",
                "url": "https://techsaas.tech"
            },
            "license": {
                "name": "Proprietary",
                "url": "https://techsaas.tech/terms"
            }
        },
        "servers": [
            {
                "url": "/api",
                "description": "TechSaaS API Gateway"
            }
        ],
        "tags": [],
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT token obtained from the authentication endpoint"
                },
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key obtained from the API key management endpoint"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "message": {"type": "string"},
                        "error": {"type": "string"}
                    },
                    "required": ["status", "message"]
                },
                "HealthCheck": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                        "version": {"type": "string"}
                    },
                    "required": ["status"]
                }
            }
        }
    }
    
    # Add common response definitions
    common_responses = {
        "401": {
            "description": "Unauthorized - Authentication required",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "403": {
            "description": "Forbidden - Insufficient permissions",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "404": {
            "description": "Not Found - Resource not found",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "500": {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        }
    }
    
    # Add basic gateway endpoints
    spec["paths"]["/health"] = {
        "get": {
            "summary": "Health check",
            "description": "Check the health status of the API Gateway",
            "operationId": "healthCheck",
            "tags": ["System"],
            "responses": {
                "200": {
                    "description": "Health check result",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HealthCheck"}
                        }
                    }
                },
                **common_responses
            }
        }
    }
    
    # Add service endpoints based on service registry
    for service_id, service_info in registry.services.items():
        # Add a tag for the service
        spec["tags"].append({
            "name": service_id,
            "description": f"API endpoints for the {service_id} service"
        })
        
        # Add a basic path entry for the service root
        spec["paths"][f"/{service_id}"] = {
            "get": {
                "summary": f"{service_id} service root",
                "description": f"Root endpoint for the {service_id} service",
                "operationId": f"{service_id}Root",
                "tags": [service_id],
                "responses": {
                    "200": {
                        "description": "Service information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    },
                    **common_responses
                }
            }
        }
    
    # Add API subscription tiers
    spec["components"]["schemas"]["SubscriptionTier"] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "rate_limit": {"type": "integer"},
            "features": {
                "type": "array",
                "items": {"type": "string"}
            },
            "price": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string"}
                }
            }
        }
    }
    
    spec["paths"]["/subscription/tiers"] = {
        "get": {
            "summary": "List API subscription tiers",
            "description": "Get information about available subscription tiers for the API",
            "operationId": "listSubscriptionTiers",
            "tags": ["Subscription"],
            "responses": {
                "200": {
                    "description": "List of subscription tiers",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "tiers": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/SubscriptionTier"}
                                    }
                                }
                            }
                        }
                    }
                },
                **common_responses
            }
        }
    }
    
    return spec

@docs_blueprint.route('/')
def docs_index():
    """Documentation index page"""
    return jsonify({
        "message": "TechSaaS API Documentation",
        "swagger_ui": "/api/docs/swagger",
        "redoc": "/api/docs/redoc",
        "openapi_spec": "/api/docs/openapi.json"
    })

@docs_blueprint.route('/openapi.json')
def openapi_spec():
    """OpenAPI specification endpoint"""
    try:
        spec = generate_openapi_spec()
        return jsonify(spec)
    except Exception as e:
        logger.error(f"Error generating OpenAPI specification: {str(e)}")
        return jsonify({"error": "Error generating OpenAPI specification"}), 500

@docs_blueprint.route('/swagger')
def swagger_ui():
    """Swagger UI endpoint"""
    # In a real implementation, this would serve the Swagger UI HTML page
    # For now, we'll just return a placeholder
    return jsonify({
        "message": "Swagger UI would be served here",
        "installation_instructions": "Install Swagger UI and serve the static files here"
    })

@docs_blueprint.route('/redoc')
def redoc():
    """ReDoc endpoint"""
    # In a real implementation, this would serve the ReDoc HTML page
    # For now, we'll just return a placeholder
    return jsonify({
        "message": "ReDoc would be served here",
        "installation_instructions": "Install ReDoc and serve the static files here"
    })

@docs_blueprint.route('/examples/<service_id>')
def service_examples(service_id):
    """API examples for a specific service"""
    # In a real implementation, this would serve service-specific examples
    return jsonify({
        "service": service_id,
        "example_endpoints": [
            {
                "path": f"/{service_id}/example1",
                "method": "GET",
                "description": "Example endpoint 1"
            },
            {
                "path": f"/{service_id}/example2",
                "method": "POST",
                "description": "Example endpoint 2"
            }
        ],
        "code_examples": {
            "python": f"import requests\n\nresponse = requests.get('https://techsaas.tech/api/{service_id}/example1')\nprint(response.json())",
            "javascript": f"fetch('https://techsaas.tech/api/{service_id}/example1')\n  .then(response => response.json())\n  .then(data => console.log(data));",
            "curl": f"curl -X GET https://techsaas.tech/api/{service_id}/example1"
        }
    })

def register_routes(app):
    """Register documentation routes with the Flask app"""
    app.register_blueprint(docs_blueprint)
    return app
