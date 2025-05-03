"""
TechSaaS Platform - AI Service Application Factory
This file contains the Flask application factory that creates and configures the Flask app
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_smorest import Api
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

# Import config
from config.config import get_config

# Import blueprints
from api.v1.routes import register_routes

# Import LangChain extension
from api.v1.services.langchain_extension import LangChain

def setup_logging(app):
    """Configure application logging"""
    log_level_str = app.config.get('LOG_LEVEL', 'INFO')
    
    # Strip comments if present (handle case where log_level includes a comment)
    if '#' in log_level_str:
        log_level_str = log_level_str.split('#')[0].strip()
    
    log_format = app.config.get('LOG_FORMAT', 
                              '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Convert string log level to numeric value
    log_level_str = log_level_str.upper()
    numeric_level = getattr(logging, log_level_str, None)
    if not isinstance(numeric_level, int):
        app.logger.warning(f'Invalid log level: {log_level_str}, defaulting to INFO')
        numeric_level = logging.INFO
    
    # Configure the root logger
    logging.basicConfig(level=numeric_level, format=log_format)
    
    # Create a logger specifically for the app
    logger = logging.getLogger(app.name)
    logger.setLevel(numeric_level)
    
    # Log to console for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handler)
    
    return logger

def register_error_handlers(app):
    """Register custom error handlers for the application"""
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions"""
        response = jsonify({
            "error": error.name,
            "message": error.description,
            "status_code": error.code
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Handle generic exceptions"""
        app.logger.exception("Unhandled exception: %s", str(error))
        
        response = jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        })
        response.status_code = 500
        return response

def setup_api_docs(app):
    """Configure API documentation with Flask-Smorest"""
    api = Api(app)
    
    # Configure OpenAPI documentation
    api.spec.components.security_scheme(
        "ApiKeyAuth", {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    )
    
    api.spec.components.security_scheme(
        "BearerAuth", {"type": "http", "scheme": "bearer"}
    )
    
    # Add documentation for API tiers and rate limits
    api.spec.tag({
        "name": "Basic Tier", 
        "description": "Endpoints available on the Basic subscription tier. Rate limit: 100 requests/minute."
    })
    
    api.spec.tag({
        "name": "Pro Tier", 
        "description": "Endpoints available on the Pro subscription tier. Rate limit: 500 requests/minute."
    })
    
    api.spec.tag({
        "name": "Enterprise Tier", 
        "description": "Endpoints available on the Enterprise subscription tier. Rate limit: 2000 requests/minute."
    })
    
    api.spec.tag({
        "name": "AI", 
        "description": "Artificial Intelligence endpoints for text, chat, and completion."
    })
    
    api.spec.tag({
        "name": "Multimodal", 
        "description": "Multimodal endpoints for image, audio, and video analysis."
    })
    
    api.spec.tag({
        "name": "Management", 
        "description": "Management endpoints for system status and administration."
    })
    
    api.spec.tag({
        "name": "Subscription", 
        "description": "Subscription management endpoints for API keys and usage tracking."
    })
    
    return api

def create_app(config_name=None):
    """
    Application factory function that creates and configures a Flask app instance
    
    Args:
        config_name (str): The configuration environment name ('dev', 'test', 'prod')
                          If None, it will be determined from environment variable
                          
    Returns:
        Flask: The configured Flask application
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config()
    app.config.from_object(config)
    
    # Set up logging
    logger = setup_logging(app)
    logger.info(f"Starting AI Service in {app.config.get('ENV', 'development')} mode")
    
    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})
    
    # Support for reverse proxies
    app.wsgi_app = ProxyFix(app.wsgi_app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Set up API documentation
    api = setup_api_docs(app)
    
    # Register API routes
    register_routes(app)
    
    # Initialize LangChain extension
    langchain = LangChain()
    langchain.init_app(app)
    
    # Log startup information
    logger.info(f"AI Service initialized with {app.config.get('DEFAULT_AI_MODEL', 'default')} model")
    logger.info(f"API documentation available at {app.config.get('OPENAPI_URL_PREFIX', '/api/docs')}")
    
    return app
