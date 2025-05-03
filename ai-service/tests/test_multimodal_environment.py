#!/usr/bin/env python3
"""
Tests for Multimodal Processing Environment and Hardware Detection

This module contains unit tests for the hardware detection and 
configuration components of the multimodal processing system.
"""

import os
import sys
import unittest
import logging
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import multimodal components
from multimodal.utils.hardware import (
    get_hardware_profile, 
    get_current_hardware_profile,
    HardwareProfile,
    GPUInfo
)
from multimodal.utils.config import (
    create_default_config,
    load_config,
    save_config,
    get_config,
    MultimodalConfig,
    ModelConfig
)
from multimodal.base import MultimodalSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultimodalEnvironmentTest")


class TestHardwareDetection(unittest.TestCase):
    """Test hardware detection functionality."""
    
    def test_hardware_profile_creation(self):
        """Test that hardware profile can be created."""
        profile = get_hardware_profile()
        self.assertIsInstance(profile, HardwareProfile)
        logger.info(f"Detected hardware profile: {profile.get_capability_level()}")
        
        # Check that basic properties are present
        self.assertTrue(hasattr(profile, 'has_gpu'))
        self.assertTrue(hasattr(profile, 'platform'))
        self.assertTrue(hasattr(profile, 'total_ram_gb'))
        self.assertTrue(hasattr(profile, 'available_ram_gb'))
        
        # Check capability level is valid
        self.assertIn(profile.get_capability_level(), ["low", "medium", "high"])
    
    def test_cached_hardware_profile(self):
        """Test that cached hardware profile works."""
        profile1 = get_current_hardware_profile()
        profile2 = get_current_hardware_profile()
        # Should be the same object
        self.assertIs(profile1, profile2)
        
        # Force refresh should give a new object
        profile3 = get_current_hardware_profile(force_refresh=True)
        self.assertIsNot(profile1, profile3)
    
    def test_model_compatibility(self):
        """Test checking model compatibility with hardware."""
        profile = get_hardware_profile()
        
        # Test with a model that should run on any hardware
        light_model = {
            "min_ram_gb": 2.0,
            "min_gpu_gb": 0.0,
            "requires_gpu": False
        }
        self.assertTrue(profile.can_run_model(light_model))
        
        # Test with a demanding model
        heavy_model = {
            "min_ram_gb": 64.0,  # Very high RAM requirement
            "min_gpu_gb": 24.0,  # Very high GPU memory
            "requires_gpu": True  # Requires GPU
        }
        # This may pass or fail depending on the hardware
        can_run = profile.can_run_model(heavy_model)
        logger.info(f"Can run heavy model: {can_run}")


class TestConfiguration(unittest.TestCase):
    """Test configuration system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary config file path
        self.temp_config_path = os.path.join(os.path.dirname(__file__), "test_config.json")
        
        # Remove any existing test config file
        if os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary config file
        if os.path.exists(self.temp_config_path):
            os.remove(self.temp_config_path)
    
    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = create_default_config()
        self.assertIsInstance(config, MultimodalConfig)
        
        # Check that basic properties are present
        self.assertTrue(hasattr(config, 'adapt_to_hardware'))
        self.assertTrue(hasattr(config, 'models'))
        self.assertIsInstance(config.processing.batch_size, int)
        
        # Check that default models are defined
        self.assertIn(config.default_image_model, config.models)
        self.assertIn(config.default_video_model, config.models)
        self.assertIn(config.default_text_model, config.models)
    
    def test_config_serialization(self):
        """Test serializing and deserializing configuration."""
        config1 = create_default_config()
        
        # Save and load configuration
        save_config(config1, self.temp_config_path)
        self.assertTrue(os.path.exists(self.temp_config_path))
        
        config2 = load_config(self.temp_config_path)
        
        # Check that models are preserved
        self.assertEqual(
            set(config1.models.keys()),
            set(config2.models.keys())
        )
        
        # Check that model properties are preserved
        for model_name in config1.models:
            model1 = config1.models[model_name]
            model2 = config2.models[model_name]
            self.assertEqual(model1.name, model2.name)
            self.assertEqual(model1.provider, model2.provider)
    
    def test_cached_config(self):
        """Test that cached config works."""
        config1 = get_config()
        config2 = get_config()
        # Should be the same object
        self.assertIs(config1, config2)
        
        # Force reload should give a new object
        config3 = get_config(reload=True)
        self.assertIsNot(config1, config3)


class TestMultimodalSystem(unittest.TestCase):
    """Test the integrated multimodal system."""
    
    def test_system_initialization(self):
        """Test initializing the multimodal system."""
        system = MultimodalSystem()
        self.assertIsInstance(system, MultimodalSystem)
        
        # Check hardware detection worked
        hw_info = system.get_hardware_info()
        self.assertTrue(hw_info["detected"])
        
        # Check suitable models are available
        image_models = system.get_suitable_image_models()
        self.assertTrue(len(image_models) > 0)
        
        # Default models should be in suitable models lists
        self.assertIn(system.get_default_model("image"), image_models)
    
    def test_system_with_forced_cpu(self):
        """Test initializing with forced CPU mode."""
        system = MultimodalSystem(force_cpu=True)
        
        # GPU preference should be disabled
        self.assertFalse(system.config.gpu_preferred)


if __name__ == "__main__":
    unittest.main()
