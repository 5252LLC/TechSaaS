"""
LangChain Flask Extension

This module provides a Flask extension for LangChain integration.
It follows the Flask extension pattern and handles proper initialization
of LangChain components during application startup.
"""

import logging
from functools import wraps
from flask import current_app, Blueprint, g

# Import LangChain factory
from api.v1.services.langchain_factory import (
    get_langchain_service,
    initialize_langchain_for_app
)

# Configure logging
logger = logging.getLogger(__name__)


class LangChain:
    """
    Flask extension for LangChain integration
    
    This extension follows the Flask extension pattern and provides
    a simple interface for integrating LangChain with Flask applications.
    
    Usage:
        from api.v1.services.langchain_extension import LangChain
        
        app = Flask(__name__)
        langchain = LangChain()
        langchain.init_app(app)
    """
    
    def __init__(self, app=None):
        """
        Initialize the extension
        
        Args:
            app: Optional Flask application instance
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize the extension with the given Flask application
        
        Args:
            app: Flask application instance
        """
        # Register extension with Flask
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['langchain'] = self
        
        # Initialize LangChain immediately - more reliable than using before_first_request
        # which is deprecated in newer Flask versions
        try:
            with app.app_context():
                self._initialize_langchain()
                app._langchain_initialized = True
        except RuntimeError:
            # Handle case where there's no application context yet
            logger.info("No application context available, will initialize LangChain on first request")
            
            # Initialize on first request as fallback
            @app.before_request
            def initialize_before_request():
                if not getattr(app, '_langchain_initialized', False):
                    self._initialize_langchain()
                    app._langchain_initialized = True
        
        # Add cleanup hook for memory management
        @app.teardown_appcontext
        def cleanup_memory(exception=None):
            # Save any active memory sessions
            if hasattr(g, 'memory_manager') and hasattr(g, 'user_id'):
                try:
                    logger.debug(f"Saving memory for user {g.user_id}")
                    g.memory_manager.save()
                except Exception as e:
                    logger.warning(f"Error saving memory for user {g.user_id}: {str(e)}")
        
        # Register the extension interface on the app
        app.langchain = self
        
        logger.info("LangChain extension registered with Flask application")
        
    def _initialize_langchain(self):
        """Initialize LangChain components when the app is ready"""
        app = self.app or current_app
        
        try:
            # Enable debug mode for LangChain
            if app.config.get('LANGCHAIN_VERBOSE', False):
                try:
                    # For langchain-core compatibility
                    import langchain_core
                    if hasattr(langchain_core, 'set_debug'):
                        logger.info("Enabling LangChain debug mode")
                        langchain_core.set_debug(True)
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Could not set LangChain debug mode: {str(e)}")
            
            # Initialize LangChain components
            initialize_langchain_for_app(app)
            
            logger.info("LangChain initialization complete")
            
        except Exception as e:
            logger.exception(f"Error during LangChain initialization: {str(e)}")
            # Don't raise to let the app continue startup
    
    def requires_langchain(self, f):
        """
        Decorator to ensure LangChain is available for a route
        
        Args:
            f: The route function to decorate
            
        Returns:
            The decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Try to get LangChain service
                service = get_langchain_service()
                
                # Make it available in Flask's g object
                g.langchain_service = service
                
                # Continue with the route
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.exception(f"LangChain service not available: {str(e)}")
                
                # If LangChain is required but not available, return an error
                from flask import jsonify
                return jsonify({
                    'status': 'error',
                    'error': 'LangChain service unavailable',
                    'message': str(e)
                }), 503
        
        return decorated_function
    
    def get_service(self):
        """
        Get the LangChain service instance
        
        Returns:
            LangChainService: The initialized service
        """
        return get_langchain_service()


# Factory function for Flask-Smorest compatibility
def create_langchain_extension(app=None):
    """
    Create a new LangChain extension instance
    
    Args:
        app: Optional Flask application instance
        
    Returns:
        LangChain: The extension instance
    """
    return LangChain(app)
