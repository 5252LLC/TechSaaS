"""
LangChain Compatibility Layer

This module provides compatibility functions for handling LangChain version
differences and deprecated attributes. It serves as a layer between our
application code and the LangChain library.
"""

import logging
import sys
import importlib.util
from typing import Any, Optional, Dict, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Keep track of patched modules
_patched_modules = set()

def detect_langchain_version() -> Tuple[int, int, int]:
    """
    Detect the installed LangChain version and return the version numbers.
    
    Returns:
        tuple: Major, minor, patch version numbers
    """
    try:
        # Check for langchain package
        if importlib.util.find_spec('langchain') is not None:
            import langchain
            version = getattr(langchain, "__version__", "0.0.0")
            major, minor, patch = map(int, version.split("."))
            return major, minor, patch
        
        # Check for langchain_core package (newer versions)
        elif importlib.util.find_spec('langchain_core') is not None:
            import langchain_core
            version = getattr(langchain_core, "__version__", "0.0.0")
            # Consider new package structure as 1.0.0+
            return 1, 0, 0  
        
        # Neither found
        else:
            logger.warning("No LangChain packages found")
            return 0, 0, 0
    
    except (ImportError, ValueError) as e:
        logger.warning(f"Error detecting LangChain version: {str(e)}")
        return 0, 0, 0

def _patch_langchain_module():
    """
    Apply monkey patch to langchain module to handle deprecated attributes
    """
    try:
        # Only patch once
        if 'langchain' in _patched_modules:
            return
            
        # Check if langchain is available
        if importlib.util.find_spec('langchain') is None:
            logger.warning("LangChain module not found, skipping patch")
            return
            
        # Import the module
        import langchain
        
        # Add the deprecated attributes with appropriate warnings
        if not hasattr(langchain, 'verbose'):
            setattr(langchain, 'verbose', False)
            logger.debug("Added compatibility attribute 'verbose' to langchain module")
            
        # Mark as patched
        _patched_modules.add('langchain')
        logger.info("LangChain compatibility patches applied")
        
    except Exception as e:
        logger.warning(f"Failed to apply LangChain compatibility patches: {str(e)}")

def _patch_langchain_core_module():
    """
    Apply monkey patch to langchain_core module for compatibility
    """
    try:
        # Only patch once
        if 'langchain_core' in _patched_modules:
            return
            
        # Check if langchain_core is available
        if importlib.util.find_spec('langchain_core') is None:
            logger.warning("LangChain Core module not found, skipping patch")
            return
            
        # Import the module
        import langchain_core
        
        # Add missing debug attribute if needed
        if not hasattr(langchain_core, '_debug'):
            setattr(langchain_core, '_debug', False)
        
        # Add missing get_debug function if needed
        if not hasattr(langchain_core, 'get_debug'):
            def get_debug() -> bool:
                """Get debug status (compatibility function)"""
                # Return debug flag if exists, otherwise False
                return getattr(langchain_core, '_debug', False)
            
            setattr(langchain_core, 'get_debug', get_debug)
            logger.debug("Added compatibility function 'get_debug' to langchain_core module")
        
        # Add missing set_debug function if needed
        if not hasattr(langchain_core, 'set_debug'):
            def set_debug(value: bool) -> None:
                """Set debug status (compatibility function)"""
                setattr(langchain_core, '_debug', value)
                
            setattr(langchain_core, 'set_debug', set_debug)
            logger.debug("Added compatibility function 'set_debug' to langchain_core module")
        
        # Mark as patched
        _patched_modules.add('langchain_core')
        logger.info("LangChain Core compatibility patches applied")
        
    except Exception as e:
        logger.warning(f"Failed to apply LangChain Core compatibility patches: {str(e)}")

def apply_all_patches():
    """
    Apply all compatibility patches for LangChain
    """
    _patch_langchain_module()
    _patch_langchain_core_module()

def use_debug_mode(enable: bool = True):
    """
    Set debug/verbose mode for LangChain in a version-compatible way
    
    Args:
        enable (bool): Whether to enable debug mode
    """
    try:
        # Try langchain_core first (newer versions)
        try:
            import langchain_core
            
            # Set _debug attribute directly (core storage)
            setattr(langchain_core, '_debug', enable)
            
            # Call set_debug if it exists
            if hasattr(langchain_core, 'set_debug'):
                langchain_core.set_debug(enable)
                
            logger.debug(f"Set langchain_core debug mode to {enable}")
            
        except (ImportError, AttributeError):
            pass
            
        # Also set legacy approach for compatibility
        try:
            import langchain
            
            # Make sure we have the attribute (should be added by patch)
            if not hasattr(langchain, 'verbose'):
                setattr(langchain, 'verbose', False)
                
            # Set the attribute
            langchain.verbose = enable
            logger.debug(f"Set langchain.verbose to {enable}")
            
        except (ImportError, AttributeError):
            pass
            
        return True
        
    except Exception as e:
        logger.warning(f"Failed to set LangChain debug mode: {str(e)}")
        return False

def get_debug_mode() -> bool:
    """
    Get current debug/verbose mode for LangChain in a version-compatible way
    
    Returns:
        bool: Current debug mode state
    """
    try:
        # Try langchain_core first (newer versions)
        try:
            import langchain_core
            
            # First try using the get_debug function if it exists
            if hasattr(langchain_core, 'get_debug'):
                return langchain_core.get_debug()
            
            # Fall back to direct attribute access
            return getattr(langchain_core, '_debug', False)
            
        except (ImportError, AttributeError):
            pass
            
        # Fallback to legacy approach
        try:
            import langchain
            
            # Make sure we have the attribute (should be added by patch)
            if not hasattr(langchain, 'verbose'):
                setattr(langchain, 'verbose', False)
                
            # Get the attribute
            return langchain.verbose
            
        except (ImportError, AttributeError):
            pass
        
        # If all else fails, return False
        return False
        
    except Exception as e:
        logger.warning(f"Failed to get LangChain debug mode: {str(e)}")
        return False

def get_llm_model_name(llm: Any) -> str:
    """
    Get model name from LLM object regardless of version.
    
    Args:
        llm: The language model object
    
    Returns:
        str: The model name or "unknown" if not found
    """
    try:
        # Modern LangChain version
        if hasattr(llm, "model_name"):
            return llm.model_name
        # Legacy version
        elif hasattr(llm, "model"):
            return llm.model
        # Fallback for custom LLMs
        else:
            return str(llm.__class__.__name__)
    except Exception as e:
        logger.warning(f"Could not extract model name: {e}")
        return "unknown"

def memory_adapter(service: Any) -> Dict:
    """
    Provide a compatible interface to access memory regardless of version.
    
    Args:
        service: The LangChainService object
        
    Returns:
        dict: Memory dictionary
    """
    # To avoid infinite recursion with the property, we need to be careful
    # First check if service has _memory attribute (internal storage)
    if hasattr(service, "_memory") and getattr(service, "_memory", None) is not None:
        return service._memory
    
    # If service has memory_manager, use its storage
    elif hasattr(service, "memory_manager") and service.memory_manager is not None:
        # Get memory from the manager if possible
        if hasattr(service.memory_manager, "get_all_memory"):
            return service.memory_manager.get_all_memory()
        elif hasattr(service.memory_manager, "memory"):
            return service.memory_manager.memory
    
    # Fall back to empty dict
    return {}

def clear_memory(service: Any, key: Optional[str] = None) -> bool:
    """
    Clear memory in a version-compatible way.
    
    Args:
        service: The LangChainService object
        key: Optional memory key to clear, if None clears all memory
        
    Returns:
        bool: Success status
    """
    try:
        # If service has memory_manager with clear_memory method
        if hasattr(service, "memory_manager") and service.memory_manager is not None:
            if hasattr(service.memory_manager, "clear_memory"):
                if key:
                    service.memory_manager.clear_memory(key)
                else:
                    service.memory_manager.clear_all_memory()
                return True
        
        # If service has direct memory attribute
        elif hasattr(service, "memory") and isinstance(service.memory, dict):
            if key:
                if key in service.memory:
                    service.memory[key] = []
                else:
                    logger.warning(f"No memory found for key '{key}' to clear")
                    return False
            else:
                service.memory.clear()
            return True
            
        return False
        
    except Exception as e:
        logger.warning(f"Failed to clear memory: {str(e)}")
        return False

# Apply patches when module is imported
apply_all_patches()
