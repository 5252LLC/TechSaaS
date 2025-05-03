#!/usr/bin/env python3
"""
Resource Management Test

Tests the resource management functionality of the multimodal system.
This test is designed to verify that the system properly handles
loading and unloading models to prevent memory overloads.
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import multimodal components
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.utils.config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResourceManagementTest")


class TestResourceManagement(unittest.TestCase):
    """Test the resource management functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create model manager with default settings
        try:
            self.model_manager = UnifiedModelManager()
        except Exception as e:
            self.skipTest(f"Could not initialize model manager: {e}")
    
    def test_resource_check(self):
        """Test the resource availability check."""
        # Test checking resource availability
        logger.info("Testing resource availability check...")
        result = self.model_manager.check_resource_availability(1.0)  # Check for 1GB
        self.assertIsInstance(result, bool, "Resource check should return a boolean")
        
        # Log system memory
        try:
            import psutil
            available_memory_gb = psutil.virtual_memory().available / (1024 * 1024 * 1024)
            logger.info(f"System has {available_memory_gb:.2f} GB available memory")
        except ImportError:
            logger.warning("psutil not available, cannot check system memory")
    
    def test_unload_all_models(self):
        """Test unloading all models."""
        # This test only verifies the method works, it doesn't actually load models
        logger.info("Testing unloading all models...")
        
        # Try unloading all models from a provider
        try:
            result = self.model_manager.unload_all_models("ollama")
            logger.info(f"Unloaded Ollama models")
        except Exception as e:
            self.fail(f"Error unloading Ollama models: {e}")
        
        # Try unloading all models
        try:
            result = self.model_manager.unload_all_models()
            logger.info(f"Unloaded all models")
        except Exception as e:
            self.fail(f"Error unloading all models: {e}")


class TestSingleModelLoading(unittest.TestCase):
    """Test loading a single model at a time."""
    
    def setUp(self):
        """Set up the test environment."""
        try:
            self.model_manager = UnifiedModelManager()
        except Exception as e:
            self.skipTest(f"Could not initialize model manager: {e}")
    
    def test_ollama_text_model_loading(self):
        """Test loading a text model from Ollama."""
        if "ollama" not in self.model_manager.available_providers:
            self.skipTest("Ollama provider not available")
        
        # Try to get a small text model from Ollama
        logger.info("Looking for a small text model from Ollama...")
        
        # List available models
        models = self.model_manager.list_models_by_provider("ollama")
        logger.info(f"Found {len(models)} Ollama models")
        
        # Find a small text model
        small_text_model = None
        for model in models:
            if "text" in model.capabilities and not "image" in model.capabilities:
                small_text_model = f"ollama/{model.name}"
                break
        
        if not small_text_model:
            small_text_model = "ollama/phi3:mini"  # Default small model
        
        logger.info(f"Selected model: {small_text_model}")
        
        # Check if model is available
        if not self.model_manager.is_model_available(small_text_model):
            self.skipTest(f"Model {small_text_model} not available")
        
        try:
            # Unload any existing models
            self.model_manager.unload_all_models()
            
            # Check resource availability
            provider, model_name = self.model_manager._parse_model_id(small_text_model)
            required_memory_gb = 2.0  # Default for small text model
            
            if not self.model_manager.check_resource_availability(required_memory_gb):
                self.skipTest(f"Insufficient memory for model {small_text_model}")
            
            # Try to load the model
            logger.info(f"Loading model {small_text_model}...")
            result = self.model_manager.load_model(small_text_model)
            
            # Verify it loaded
            loaded = self.model_manager.is_model_loaded(small_text_model)
            
            logger.info(f"Model {small_text_model} loaded: {loaded}")
            
            # Unload the model
            logger.info(f"Unloading model {small_text_model}...")
            self.model_manager.unload_model(small_text_model)
            
            # Verify it unloaded
            still_loaded = self.model_manager.is_model_loaded(small_text_model)
            logger.info(f"Model still loaded: {still_loaded}")
            
            self.assertFalse(still_loaded, "Model should be unloaded")
            
        except Exception as e:
            logger.error(f"Error during model loading test: {e}")
            self.fail(str(e))


def run_focused_test():
    """Run a focused test without using unittest."""
    logger.info("Running focused resource management test...")
    
    try:
        # Initialize model manager
        model_manager = UnifiedModelManager()
        
        # Check system resources
        try:
            import psutil
            mem = psutil.virtual_memory()
            logger.info(f"System memory: {mem.total / (1024**3):.2f} GB total, "
                      f"{mem.available / (1024**3):.2f} GB available")
        except ImportError:
            logger.warning("psutil not available, cannot check system memory")
        
        # Check if Ollama is available
        if "ollama" in model_manager.available_providers:
            logger.info("Ollama provider is available")
            
            # Test resource check
            has_resources = model_manager.check_resource_availability(2.0)
            logger.info(f"Has resources for 2GB model: {has_resources}")
            
            # Test unloading all models
            model_manager.unload_all_models()
            logger.info("Successfully unloaded all models")
            
            logger.info("Resource management test completed successfully")
            return True
        else:
            logger.warning("Ollama provider not available, skipping test")
            return False
            
    except Exception as e:
        logger.error(f"Error during focused test: {e}")
        return False


if __name__ == "__main__":
    # Choose one of these methods to run:
    
    # Option 1: Run the full unittest suite
    # unittest.main()
    
    # Option 2: Run a focused test without unittest
    success = run_focused_test()
    if success:
        logger.info("Focused test passed")
    else:
        logger.error("Focused test failed")
