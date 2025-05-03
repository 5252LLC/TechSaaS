"""
Routes package initialization
Imports and registers all route blueprints
"""

from flask import Flask, Blueprint

from .ai_endpoints import ai_blueprint
from .multimodal_endpoints import multimodal_blueprint
from .management_endpoints import management_blueprint
from .subscription_endpoints import subscription_blueprint
from .admin_endpoints import admin_blueprint
from .admin_docs import admin_docs_blueprint
from .validation_example import validation_example_blueprint
from .langchain_example import langchain_example_blueprint
from .response_example import response_example_bp
from .live_demo import live_demo_bp

__all__ = [
    'ai_blueprint',
    'multimodal_blueprint',
    'management_blueprint',
    'subscription_blueprint',
    'admin_blueprint',
    'admin_docs_blueprint',
    'validation_example_blueprint',
    'langchain_example_blueprint',
    'response_example_bp',
    'live_demo_bp',
    'register_routes'
]

def register_routes(app: Flask) -> Flask:
    """
    Register all route blueprints with the Flask app
    
    Args:
        app (Flask): Flask application instance
        
    Returns:
        Flask: Modified Flask application with registered routes
    """
    app.register_blueprint(ai_blueprint, url_prefix='/api/v1/ai')
    app.register_blueprint(multimodal_blueprint, url_prefix='/api/v1/multimodal')
    app.register_blueprint(management_blueprint, url_prefix='/api/v1/management')
    app.register_blueprint(subscription_blueprint, url_prefix='/api/v1/subscription')
    app.register_blueprint(admin_blueprint, url_prefix='/api/v1/admin')
    app.register_blueprint(admin_docs_blueprint, url_prefix='/api/v1/admin-docs')
    app.register_blueprint(validation_example_blueprint)  # URL prefix is set in the blueprint
    app.register_blueprint(langchain_example_blueprint)  # URL prefix is set in the blueprint
    app.register_blueprint(response_example_bp)  # URL prefix is set in the blueprint
    app.register_blueprint(live_demo_bp)  # URL prefix is set in the blueprint
    
    app.logger.info("All API route blueprints registered")
    return app
