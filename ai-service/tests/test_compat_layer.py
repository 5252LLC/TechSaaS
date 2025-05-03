#!/usr/bin/env python3
"""
Simple test script for LangChain compatibility layer.
This script tests the basic functionality of the compatibility layer
without running the full test suite.
"""

import os
import sys
import logging

# Add the parent directory to the Python path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger("CompatLayerTest")

def test_version_detection():
    """Test version detection functionality."""
    from langchain.compat import detect_langchain_version
    
    logger.info("Testing version detection...")
    major, minor, patch = detect_langchain_version()
    logger.info(f"Detected LangChain version: {major}.{minor}.{patch}")
    
    # Basic version check
    assert isinstance(major, int), "Major version should be an integer"
    assert isinstance(minor, int), "Minor version should be an integer"
    assert isinstance(patch, int), "Patch version should be an integer"
    
    logger.info("Version detection test passed.")
    return True

def test_debug_mode():
    """Test debug mode functions."""
    from langchain.compat import use_debug_mode, get_debug_mode
    
    logger.info("Testing debug mode functions...")
    
    # Test setting debug mode
    initial_state = get_debug_mode()
    logger.info(f"Initial debug mode: {initial_state}")
    
    # Toggle debug mode
    use_debug_mode(not initial_state)
    new_state = get_debug_mode()
    logger.info(f"Changed debug mode to: {new_state}")
    
    # Verify change
    assert new_state != initial_state, "Debug mode should have toggled"
    
    # Reset to initial state
    use_debug_mode(initial_state)
    reset_state = get_debug_mode()
    logger.info(f"Reset debug mode to: {reset_state}")
    
    # Verify reset
    assert reset_state == initial_state, "Debug mode should have reset"
    
    logger.info("Debug mode test passed.")
    return True

def test_memory_adapter():
    """Test memory adapter functionality."""
    from langchain.compat import memory_adapter
    
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

def test_clear_memory():
    """Test memory clearing functionality."""
    from langchain.compat import clear_memory
    
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

def run_all_tests():
    """Run all compatibility layer tests."""
    logger.info("Starting LangChain compatibility layer tests...")
    
    tests = [
        test_version_detection,
        test_debug_mode,
        test_memory_adapter,
        test_clear_memory,
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
        logger.info("All compatibility layer tests passed!")
    else:
        logger.error("Some compatibility layer tests failed.")
    
    return success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
