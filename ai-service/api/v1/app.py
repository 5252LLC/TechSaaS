"""
TechSaaS API Application

This module initializes the Flask application and registers all
required extensions, blueprints, and routes.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

from api.v1.models.base import db
from api.v1.routes.audit import audit_bp
from api.v1.routes.auth_endpoints import auth_bp
from api.v1.routes.test_routes import test_bp
from api.v1.config.audit import configure_audit
from api.v1.extensions.audit import init_audit_trail
from api.v1.middleware.security_headers import security_headers_middleware
from api.v1.middleware.authorization import init_authorization_middleware


def create_app(config_name='default'):
    """
    Create and configure the Flask application.
    
    Args:
        config_name: Name of the configuration to use
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name == 'testing':
        app.config.from_object('api.v1.config.TestingConfig')
    elif config_name == 'production':
        app.config.from_object('api.v1.config.ProductionConfig')
    else:
        app.config.from_object('api.v1.config.DevelopmentConfig')
    
    # Set up CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize database
    db.init_app(app)
    
    # Configure audit trail
    configure_audit(app)
    
    # Initialize audit trail extension
    audit_trail = init_audit_trail(app, db)
    
    # Apply security headers middleware
    security_headers_middleware(app)
    
    # Initialize authorization middleware
    init_authorization_middleware(app)
    
    # Register blueprints
    app.register_blueprint(audit_bp)
    app.register_blueprint(auth_bp)
    
    # Register test routes blueprint if in testing mode or explicitly enabled
    is_testing = config_name == 'testing' or os.environ.get('ENABLE_TEST_ROUTES', 'False').lower() == 'true'
    if is_testing:
        app.register_blueprint(test_bp)
        app.logger.info("Test routes have been enabled - FOR TESTING ONLY")
    
    # Generic error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'message': 'Resource not found',
            'error': str(error)
        }), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(error)
        }), 500
    
    # API status endpoint
    @app.route('/api/v1/status')
    def status():
        return jsonify({
            'status': 'success',
            'message': 'TechSaaS API is running',
            'version': '1.0.0',
            'environment': config_name
        })
    
    # Create tables if not exist
    with app.app_context():
        db.create_all()
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
