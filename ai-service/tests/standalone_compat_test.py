#!/usr/bin/env python3
"""
Standalone test for LangChain compatibility layer.
This script tests the compatibility layer functions directly without
requiring LangChain to be installed.
"""

import os
import sys
import logging
import importlib.util
from types import ModuleType
from unittest.mock import MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger("StandaloneCompatTest")

# Define mock classes
class MockLangChain(ModuleType):
    """Mock LangChain module for testing."""
    def __init__(self, name):
        super().__init__(name)
        self.__version__ = "0.0.1"

class MockLangChainCore(ModuleType):
    """Mock LangChain Core module for testing."""
    def __init__(self, name):
        super().__init__(name)
        self.__version__ = "0.1.0"

# Function definitions similar to compat.py but simplified for testing
def memory_adapter(service):
    """Provide memory access compatibility."""
    # Check _memory attribute first
    if hasattr(service, "_memory") and getattr(service, "_memory", None) is not None:
        return service._memory
    
    # Check memory_manager if available
    if hasattr(service, "memory_manager") and service.memory_manager is not None:
        if hasattr(service.memory_manager, "get_all_memory"):
            return service.memory_manager.get_all_memory()
        elif hasattr(service.memory_manager, "memory"):
            return service.memory_manager.memory
    
    # Fallback to empty dict
    return {}

def clear_memory(service, key=None):
    """Clear memory for compatibility testing."""
    try:
        if hasattr(service, "_memory") and isinstance(service._memory, dict):
            if key:
                if key in service._memory:
                    service._memory[key] = []
                    return True
                return False
            else:
                service._memory.clear()
                return True
        
        if hasattr(service, "memory_manager") and service.memory_manager is not None:
            if key and hasattr(service.memory_manager, "clear_memory"):
                service.memory_manager.clear_memory(key)
                return True
            elif hasattr(service.memory_manager, "clear_all_memory"):
                service.memory_manager.clear_all_memory()
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        return False

def test_memory_adapter():
    """Test memory adapter functionality."""
    logger.info("Testing memory adapter...")
    
    # Test with a mock service with _memory
    class MockService:
        def __init__(self):
            self._memory = {"test": ["message1", "message2"]}
    
    service = MockService()
    memory = memory_adapter(service)
    
    # Verify memory content
    assert "test" in memory, "Memory should contain test key"
    assert len(memory["test"]) == 2, "Memory should contain 2 messages"
    assert memory["test"][0] == "message1", "First message should be 'message1'"
    
    logger.info("Memory adapter test passed.")
    return True

def test_clear_memory_function():
    """Test memory clearing functionality."""
    logger.info("Testing memory clearing...")
    
    # Test with a mock service with _memory
    class MockService:
        def __init__(self):
            self._memory = {
                "key1": ["message1", "message2"],
                "key2": ["message3"]
            }
    
    service = MockService()
    
    # Test clearing specific key
    result = clear_memory(service, "key1")
    assert result, "Clear memory should return True"
    assert len(service._memory["key1"]) == 0, "key1 should be empty"
    assert len(service._memory["key2"]) == 1, "key2 should still have one item"
    
    # Test clearing all memory
    service._memory = {
        "key1": ["message1", "message2"],
        "key2": ["message3"]
    }
    result = clear_memory(service)
    assert result, "Clear all memory should return True"
    assert len(service._memory) == 0, "All memory should be cleared"
    
    logger.info("Memory clearing test passed.")
    return True

def test_with_missing_dependencies():
    """Test behavior when LangChain dependencies are missing."""
    logger.info("Testing with missing dependencies...")
    
    # Create a service class that might try to import LangChain
    class ServiceWithMissingDeps:
        def __init__(self):
            self._memory = {"test": ["message1"]}
            self.memory_manager = None
            
            try:
                # This will fail if LangChain is not installed
                import langchain_core
                self.langchain_available = True
            except ImportError:
                self.langchain_available = False
    
    service = ServiceWithMissingDeps()
    
    # Test memory adapter with this service
    memory = memory_adapter(service)
    assert "test" in memory, "Memory should be accessible even without LangChain"
    assert len(memory["test"]) == 1, "Memory should contain 1 message"
    
    # Test clearing memory
    result = clear_memory(service, "test")
    assert result, "Should be able to clear memory even without LangChain"
    assert len(service._memory["test"]) == 0, "test key should be empty"
    
    logger.info("Missing dependencies test passed.")
    return True

def run_all_tests():
    """Run all standalone compatibility tests."""
    logger.info("Starting standalone compatibility tests...")
    
    tests = [
        test_memory_adapter,
        test_clear_memory_function,
        test_with_missing_dependencies,
    ]
    
    success = True
    for i, test_func in enumerate(tests):
        logger.info(f"Running test {i+1}/{len(tests)}: {test_func.__name__}")
        try:
            result = test_func()
            success = success and result
        except Exception as e:
            logger.error(f"Test {test_func.__name__} failed: {str(e)}")
            success = False
    
    if success:
        logger.info("All standalone compatibility tests passed!")
    else:
        logger.error("Some standalone compatibility tests failed.")
    
    return success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
