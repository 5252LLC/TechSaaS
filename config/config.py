"""
TechSaaS Application Configuration

This module contains configuration settings for different environments
(development, testing, production).
"""
import os
from pathlib import Path

# Base directory of the application
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Base configuration class with settings common to all environments"""
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string-for-development'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-for-development'
    
    # Database settings - using SQLite by default
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Cache settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    
    # Ensure upload directory exists
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    
    # Scraper settings
    PROXY_ENABLED = os.environ.get('PROXY_ENABLED') or True
    PROXY_ROTATION = os.environ.get('PROXY_ROTATION') or True
    
    # Video extractor settings
    VIDEO_CACHE_TIMEOUT = 86400  # 24 hours
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        pass


class DevelopmentConfig(Config):
    """Configuration for development environment"""
    DEBUG = True
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True  # Log SQL queries
    TEMPLATES_AUTO_RELOAD = True
    
    # Development mail settings (if not using environment variables)
    MAIL_SUPPRESS_SEND = True  # Don't send actual emails in development
    
    # Temporarily disable CSRF for testing
    WTF_CSRF_ENABLED = False


class TestingConfig(Config):
    """Configuration for testing environment"""
    TESTING = True
    
    # Use in-memory SQLite database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF protection in tests
    WTF_CSRF_ENABLED = False
    
    # Don't send emails during tests
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    """Configuration for production environment"""
    # Use stronger secret key in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'production-jwt-secret'
    
    # Disable debug mode
    DEBUG = False
    
    # Configure for ProtonMail SMTP if using custom domain
    # Note: Update these when ProtonMail business account is set up
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.protonmail.ch'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    
    # Production should always use https
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # More aggressive caching in production
    CACHE_TYPE = 'FileSystemCache'
    CACHE_DIR = os.path.join(basedir, 'cache')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour
    
    # Ensure cache directory exists
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def init_app(app):
        """Additional production-specific initialization"""
        Config.init_app(app)
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


# Configuration dictionary mapping environment names to config classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig
}
