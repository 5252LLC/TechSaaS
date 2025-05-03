"""
LangChain Factory Module for Flask API Integration

This module provides factory functions and integration helpers for initializing
and managing LangChain components within the Flask API.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
from flask import current_app, g

# Import LangChain service
from langchain.service import LangChainService
from langchain.memory.simple import SimpleMemoryManager
from langchain.memory.persistent import PersistentMemoryManager

# Configure logging
logger = logging.getLogger(__name__)

# Singleton instance to maintain across requests
_langchain_service_instance = None

def get_langchain_service(reinitialize=False) -> LangChainService:
    """
    Get or create a singleton instance of the LangChainService
    
    Args:
        reinitialize (bool): Force reinitialization of the service
        
    Returns:
        LangChainService: The initialized LangChain service
    """
    global _langchain_service_instance
    
    if _langchain_service_instance is None or reinitialize:
        # Initialize from Flask app configuration
        config = current_app.config
        
        model_name = config.get('DEFAULT_AI_MODEL', 'ollama/llama2')
        ollama_base_url = config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        
        # If model name has a provider prefix (e.g., ollama/llama2), extract just the model name
        if '/' in model_name:
            model_name = model_name.split('/')[1]
        
        # Get model configuration
        model_kwargs = {
            'temperature': config.get('DEFAULT_TEMPERATURE', 0.7),
            'max_tokens': config.get('DEFAULT_MAX_TOKENS', 2048)
        }
        
        # Get memory configuration
        memory_dir = config.get('MEMORY_DIR', '/tmp/techsaas-memory')
        persistent_memory = config.get('PERSISTENT_MEMORY', True)
        encryption_enabled = config.get('MEMORY_ENCRYPTION', False)
        encryption_key = config.get('MEMORY_ENCRYPTION_KEY', None)
        
        # Create instance
        try:
            _langchain_service_instance = LangChainService(
                model_name=model_name,
                ollama_base_url=ollama_base_url,
                model_kwargs=model_kwargs,
                memory_dir=memory_dir,
                persistent_memory=persistent_memory,
                encryption_enabled=encryption_enabled,
                encryption_key=encryption_key
            )
            
            # Configure debug/verbose mode
            debug_enabled = config.get('LANGCHAIN_VERBOSE', False)
            if debug_enabled:
                logger.info("Enabling LangChain debug mode")
                try:
                    # For langchain-core compatibility
                    import langchain_core
                    if hasattr(langchain_core, 'set_debug'):
                        langchain_core.set_debug(True)
                except (ImportError, AttributeError):
                    logger.warning("Could not set langchain_core debug mode")
            
            # Configure caching if enabled
            if config.get('LANGCHAIN_CACHE', True):
                _langchain_service_instance.enable_caching()
                
            logger.info("LangChain Service initialized successfully")
            
        except Exception as e:
            logger.exception(f"Error initializing LangChain service: {str(e)}")
            raise
    
    return _langchain_service_instance

def get_user_memory_manager(user_id: str) -> Union[SimpleMemoryManager, PersistentMemoryManager]:
    """
    Get a memory manager instance for the specific user
    
    Args:
        user_id (str): Unique identifier for the user
        
    Returns:
        Union[SimpleMemoryManager, PersistentMemoryManager]: Memory manager for the user
    """
    langchain_service = get_langchain_service()
    return langchain_service.get_memory_manager(user_id)

def create_chain_for_task(task_type: str, user_id: Optional[str] = None) -> Any:
    """
    Create a LangChain chain configured for a specific task
    
    Args:
        task_type (str): Type of task ('conversation', 'summarization', 'analysis', etc.)
        user_id (str, optional): User ID for memory context, if applicable
        
    Returns:
        Any: The configured LangChain chain
    """
    langchain_service = get_langchain_service()
    
    # Get memory manager if user_id is provided
    memory_manager = None
    if user_id:
        memory_manager = get_user_memory_manager(user_id)
    
    # Create chain based on task type
    if task_type == 'conversation':
        return langchain_service.create_conversation_chain(memory_manager=memory_manager)
    elif task_type == 'summarization':
        return langchain_service.create_summarization_chain()
    elif task_type == 'analysis':
        return langchain_service.create_analysis_chain()
    else:
        logger.warning(f"Unknown task type: {task_type}, falling back to default chain")
        return langchain_service.create_default_chain()

def initialize_langchain_for_app(app) -> None:
    """
    Initialize LangChain integration for the Flask application
    
    Args:
        app: Flask application instance
        
    Returns:
        None
    """
    try:
        # Initialize LangChain from app config
        logger.info("Initializing LangChain for application")
        
        model_name = app.config.get('DEFAULT_AI_MODEL', 'ollama/llama2')
        logger.info(f"Using model: {model_name}")
        
        # Create LangChain service instance
        service = get_langchain_service(reinitialize=True)
        
        # Register cleanup function
        @app.teardown_appcontext
        def cleanup_langchain(_):
            """Clean up LangChain resources when app context ends"""
            logger.debug("Cleaning up LangChain resources")
            # Any cleanup needed
            
        logger.info("LangChain initialization complete")
        
    except Exception as e:
        logger.exception(f"Error initializing LangChain for app: {str(e)}")
        # Don't re-raise to avoid crashing app startup
        # The app should degrade gracefully if LangChain is not available

def register_langchain_extension(app) -> None:
    """
    Register LangChain as a Flask extension
    
    Args:
        app: Flask application instance
        
    Returns:
        None
    """
    from api.v1.services.langchain_extension import LangChain
    
    langchain = LangChain()
    langchain.init_app(app)
    
    logger.info("LangChain Flask extension registered")
