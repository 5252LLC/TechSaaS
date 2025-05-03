"""
Service Initialization

Initialize rate limiter, usage tracker, and billing service components.
"""

import logging
from flask import Flask
from .rate_limiter import rate_limiter
from .usage_tracker import usage_tracker
from .billing_service import billing_service

# Setup logger
logger = logging.getLogger(__name__)

def init_app_services(app):
    """
    Initialize all service components with the Flask app context.
    
    Args:
        app: Flask application instance
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    success = True
    
    # Initialize rate limiter
    try:
        redis_url = app.config.get('REDIS_URL')
        if redis_url and app.config.get('RATE_LIMIT_ENABLED', False):
            # Configure rate limits from application config
            rate_limits = {
                'free': {
                    'minute': app.config.get('RATE_LIMIT_FREE', 20),
                    'hour': app.config.get('RATE_LIMIT_FREE', 20) * 5,
                    'day': app.config.get('RATE_LIMIT_FREE', 20) * 50
                },
                'basic': {
                    'minute': app.config.get('RATE_LIMIT_BASIC', 100),
                    'hour': app.config.get('RATE_LIMIT_BASIC', 100) * 10,
                    'day': app.config.get('RATE_LIMIT_BASIC', 100) * 100
                },
                'pro': {
                    'minute': app.config.get('RATE_LIMIT_PRO', 500),
                    'hour': app.config.get('RATE_LIMIT_PRO', 500) * 10,
                    'day': app.config.get('RATE_LIMIT_PRO', 500) * 200
                },
                'enterprise': {
                    'minute': app.config.get('RATE_LIMIT_ENTERPRISE', 2000),
                    'hour': app.config.get('RATE_LIMIT_ENTERPRISE', 2000) * 10,
                    'day': 0  # Unlimited
                }
            }
            
            # Initialize rate limiter with Redis connection
            rate_limiter.init_redis(redis_url, rate_limits)
            app.rate_limiter = rate_limiter
            logger.info("Rate limiter initialized with Redis")
        else:
            logger.warning("Rate limiting disabled or Redis URL not configured")
    except Exception as e:
        logger.error(f"Failed to initialize rate limiter: {e}")
        success = False
    
    # Initialize usage tracker
    try:
        if redis_url and app.config.get('USAGE_TRACKING_ENABLED', False):
            # Initialize usage tracker with Redis connection
            usage_tracker.init_redis(
                redis_url, 
                async_tracking=app.config.get('USAGE_TRACKING_ASYNC', True),
                retention_days=app.config.get('USAGE_TRACKING_RETENTION_DAYS', 90)
            )
            app.usage_tracker = usage_tracker
            logger.info("Usage tracker initialized with Redis")
        else:
            logger.warning("Usage tracking disabled or Redis URL not configured")
    except Exception as e:
        logger.error(f"Failed to initialize usage tracker: {e}")
        success = False
    
    # Initialize billing service
    try:
        if redis_url and app.config.get('BILLING_ENABLED', False):
            # Initialize billing service with Redis connection
            billing_service.redis_url = redis_url
            billing_service.redis = None  # Reset connection to create a new one
            
            # Attempt Redis connection
            import redis
            billing_service.redis = redis.from_url(redis_url)
            
            # Make billing service available in app context
            app.billing_service = billing_service
            logger.info("Billing service initialized with Redis")
        else:
            logger.warning("Billing disabled or Redis URL not configured")
    except Exception as e:
        logger.error(f"Failed to initialize billing service: {e}")
        success = False
    
    return success
