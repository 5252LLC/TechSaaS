"""
TechSaaS Platform - API Gateway Service
Main API Gateway service that routes requests to appropriate microservices
"""
import os
import logging
from flask import Flask, request, jsonify, render_template

# Import middleware and services
from middleware.request_transform import init_request_middleware
from middleware.response_transform import init_response_middleware
from middleware.security import init_security_middleware
from services.service_discovery import init_service_discovery
from routes.api_routes import register_routes as register_api_routes
from routes.docs_routes import register_routes as register_docs_routes
from routes.monetization_routes import register_routes as register_monetization_routes

# Import configuration
from config.services import (
    API_GATEWAY_PORT, 
    SERVICES, 
    LOG_LEVEL, 
    LOG_FORMAT,
    ENABLE_SERVICE_DISCOVERY,
    ENABLE_CIRCUIT_BREAKER,
    ENABLE_RATE_LIMITING,
    RATE_LIMIT_PER_MINUTE,
    JWT_SECRET_KEY,
    AUTH_REQUIRED_PATHS
)

# Configure logging
log_level_value = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=log_level_value, format=LOG_FORMAT)
logger = logging.getLogger("api_gateway")

def create_app():
    """
    Create and configure the Flask application
    
    Returns:
        Flask: The configured Flask application
    """
    app = Flask(__name__)
    
    # Configure the application
    app.config.update({
        'API_GATEWAY_PORT': API_GATEWAY_PORT,
        'API_GATEWAY_VERSION': '1.0.0',
        'API_VERSION': 'v1',
        'ENABLE_SERVICE_DISCOVERY': ENABLE_SERVICE_DISCOVERY,
        'ENABLE_CIRCUIT_BREAKER': ENABLE_CIRCUIT_BREAKER,
        'ENABLE_RATE_LIMITING': ENABLE_RATE_LIMITING,
        'RATE_LIMIT_PER_MINUTE': RATE_LIMIT_PER_MINUTE,
        'JWT_SECRET_KEY': JWT_SECRET_KEY or 'techsaas-secure-jwt-key-for-development',
        'AUTH_REQUIRED_PATHS': AUTH_REQUIRED_PATHS,
    })
    
    # Initialize middleware
    init_request_middleware(app)
    init_response_middleware(app)
    init_security_middleware(app)
    
    # Initialize service discovery
    init_service_discovery(app)
    
    # Register routes
    register_api_routes(app)
    register_docs_routes(app)
    register_monetization_routes(app)
    
    # Root route
    @app.route('/')
    def index():
        """Root endpoint that provides a web interface to the API Gateway"""
        # Get service statuses
        service_statuses = {}
        if app.config.get('ENABLE_SERVICE_DISCOVERY'):
            from services.service_discovery import get_registry
            registry = get_registry()
            for service_id in SERVICES:
                try:
                    is_healthy = registry.check_service_health(service_id)
                    service_statuses[service_id] = "Healthy" if is_healthy else "Unhealthy"
                except Exception as e:
                    logger.error(f"Error checking health for service {service_id}: {str(e)}")
                    service_statuses[service_id] = "Unknown"
        
        # Check if this is an API client requesting JSON instead of HTML
        accept_header = request.headers.get('Accept', '')
        if 'application/json' in accept_header:
            # Return JSON response for API clients
            return jsonify({
                "name": "TechSaaS API Gateway",
                "version": app.config.get('API_GATEWAY_VERSION'),
                "documentation": "/api/docs",
                "services": list(SERVICES.keys()),
                "monetization": "/api/monetization/tiers"
            })
        
        # For browser requests, render the HTML template
        return render_template('index.html', 
                               version=app.config.get('API_GATEWAY_VERSION'),
                               services=SERVICES.keys(),
                               service_statuses=service_statuses,
                               status="Healthy")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "message": "Resource not found",
            "error": str(error)
        }), 404
    
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {str(error)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(error)
        }), 500
    
    logger.info(f"API Gateway initialized with configuration: {app.config}")
    return app

if __name__ == '__main__':
    app = create_app()
    port = app.config.get('API_GATEWAY_PORT', 5000)
    
    logger.info(f"Starting API Gateway service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
