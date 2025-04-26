"""
TechSaaS - Flask Application Factory

This module contains the application factory for creating Flask app instances.
It initializes extensions, registers blueprints, and configures the application.
"""

import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
cache = Cache()
jwt = JWTManager()
mail = Mail()

def create_app(config_name=None):
    """
    Application factory function.
    
    Args:
        config_name: The configuration to use (development, testing, production)
        
    Returns:
        A configured Flask application instance
    """
    # Create the Flask application instance
    app = Flask(__name__)
    
    # Determine configuration to use
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) if hasattr(config[config_name], 'init_app') else None
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    cache.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    
    # Fix for when behind proxy server
    if app.config.get('SSL_REDIRECT', False):
        app.wsgi_app = ProxyFix(app.wsgi_app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Register shell context
    register_shell_context(app)
    
    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app

def register_blueprints(app):
    """Register Flask blueprints"""
    # Import blueprints
    from app.routes.main import main_bp
    from app.routes.scraper import scraper_bp
    from app.routes.video import video_bp
    from app.routes.crypto import crypto_bp
    from app.routes.agent import agent_bp
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(scraper_bp, url_prefix='/scraper')
    app.register_blueprint(video_bp, url_prefix='/video')
    app.register_blueprint(crypto_bp, url_prefix='/crypto')
    app.register_blueprint(agent_bp, url_prefix='/agent')

def register_error_handlers(app):
    """Register custom error handlers"""
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

def register_context_processors(app):
    """Register context processors for templates"""
    
    # Brand information context processor
    from app.context_processors import inject_brand
    app.context_processor(inject_brand)
    
    # Utility context processor
    @app.context_processor
    def utility_processor():
        """Add utility functions to template context"""
        from datetime import datetime
        return {
            'now': datetime.utcnow(),
            'format_date': lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S')
        }

def register_shell_context(app):
    """Register shell context objects"""
    
    @app.shell_context_processor
    def make_shell_context():
        """Add objects to the shell context for 'flask shell'"""
        from app.models.user import User
        from app.models.scraped_data import ScrapedData
        from app.models.scraped_video import ScrapedVideo
        
        return {
            'db': db,
            'User': User,
            'ScrapedData': ScrapedData,
            'ScrapedVideo': ScrapedVideo
        }