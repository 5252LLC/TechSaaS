"""
TechSaaS Platform - Configuration

This module contains the configuration settings for the TechSaaS platform.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = False
    TESTING = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_STRATEGY = 'redis'
    RATE_LIMIT_FALLBACK_STRATEGY = 'fixed'
    
    # Tier-based Rate Limits (requests per minute)
    RATE_LIMIT_FREE = 20
    RATE_LIMIT_BASIC = 100
    RATE_LIMIT_PRO = 500
    RATE_LIMIT_ENTERPRISE = 2000
    
    # Usage Tracking Configuration
    USAGE_TRACKING_ENABLED = True
    USAGE_TRACKING_PERSISTENCE = True
    USAGE_TRACKING_ASYNC = True
    USAGE_TRACKING_RETENTION_DAYS = 90
    
    # Billing Configuration
    BILLING_ENABLED = True
    BILLING_CURRENCY = 'USD'
    BILLING_INVOICE_PREFIX = 'INV'
    BILLING_PAYMENT_GRACE_PERIOD_DAYS = 30
    BILLING_CACHE_TTL = 86400  # 24 hours

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
    # For development, allow localhost
    CORS_ORIGIN = '*'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable rate limiting for tests
    RATE_LIMIT_ENABLED = False
    
    # Use mock billing for tests
    BILLING_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    # These would be set by environment variables in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    
    # Production would use a more robust Redis setup
    REDIS_URL = os.getenv('REDIS_URL')
    
    # In production, specify allowed origins
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', 'https://techsaas.tech')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Select configuration
def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, config['default'])
