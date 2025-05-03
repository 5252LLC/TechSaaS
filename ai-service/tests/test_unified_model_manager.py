#!/usr/bin/env python3
"""
Tests for Unified Model Manager

This module contains tests for the unified model manager system,
which coordinates between different model providers.
"""

import os
import sys
import unittest
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import multimodal components
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.models.base_manager import ModelInfo, BaseModelManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedModelManagerTest")


class MockModelManager(BaseModelManager):
    """Mock model manager for testing."""
    
    def __init__(self, provider_name, available_models=None):
        """Initialize with mock model data."""
        self.provider_name = provider_name
        self._available_models = available_models or []
        self._installed_models = []
        self._loaded_models = set()
    
    def list_available_models(self):
        """Return available models."""
        return self._available_models
    
    def list_installed_models(self):
        """Return installed models."""
        return self._installed_models
    
    def get_model_info(self, model_name):
        """Get info for a specific model."""
        for model in self._available_models:
            if model.name == model_name:
                return model
        return None
    
    def download_model(self, model_name):
        """Mock downloading a model."""
        model = self.get_model_info(model_name)
        if model:
            self._installed_models.append(model)
            return True
        return False
    
    def load_model(self, model_name):
        """Mock loading a model."""
        if self.is_model_available(model_name):
            self._loaded_models.add(model_name)
            return True
        return False
    
    def unload_model(self, model_name):
        """Mock unloading a model."""
        if model_name in self._loaded_models:
            self._loaded_models.remove(model_name)
            return True
        return False
    
    def is_model_available(self, model_name):
        """Check if model is available."""
        return any(model.name == model_name for model in self._installed_models)
    
    def is_model_loaded(self, model_name):
        """Check if model is loaded."""
        return model_name in self._loaded_models


class TestUnifiedModelManager(unittest.TestCase):
    """Test the unified model manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock model data
        self.ollama_models = [
            ModelInfo(
                name="llama3:latest",
                provider="ollama",
                size_mb=4200,
                tags=["llm", "text", "large"],
                capabilities=["text"]
            ),
            ModelInfo(
                name="phi3-vision:latest",
                provider="ollama",
                size_mb=2800,
                tags=["vision", "text", "multimodal"],
                capabilities=["image", "text"]
            )
        ]
        
        self.hf_models = [
            ModelInfo(
                name="microsoft/phi-3-mini",
                provider="huggingface",
                size_mb=1500,
                tags=["text", "small"],
                capabilities=["text"]
            ),
            ModelInfo(
                name="microsoft/phi-3-vision-128k",
                provider="huggingface",
                size_mb=3800,
                tags=["vision", "multimodal", "phi"],
                capabilities=["image", "text"]
            ),
            ModelInfo(
                name="Salesforce/blip2-opt-2.7b",
                provider="huggingface",
                size_mb=5400,
                tags=["vision", "multimodal", "large"],
                capabilities=["image", "text"]
            )
        ]
        
        # Create mock managers
        self.ollama_manager = MockModelManager("ollama", self.ollama_models)
        self.hf_manager = MockModelManager("huggingface", self.hf_models)
        
        # Pre-install some models
        self.ollama_manager.download_model("llama3:latest")
        self.hf_manager.download_model("microsoft/phi-3-mini")
        
        # Create patches
        self.patches = [
            patch("multimodal.models.unified_manager.get_config", return_value=MagicMock())
        ]
        
        # Start patches
        for p in self.patches:
            p.start()
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop patches
        for p in self.patches:
            p.stop()
    
    def test_initialization(self):
        """Test initialization with mock managers."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0  # Disable cache TTL for testing
                manager.config = MagicMock()
                
                self.assertEqual(set(manager.list_active_providers()), {"ollama", "huggingface"})
    
    def test_list_available_models(self):
        """Test listing available models."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                
                # Force cache refresh
                manager._refresh_cache(force=True)
                
                models = manager.list_available_models()
                self.assertEqual(len(models), 5)  # 2 from Ollama + 3 from HF
    
    def test_get_model_info(self):
        """Test getting model info."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                
                # Force cache refresh
                manager._refresh_cache(force=True)
                
                # Test with fully qualified model ID
                model1 = manager.get_model_info("ollama/llama3:latest")
                self.assertIsNotNone(model1)
                self.assertEqual(model1.name, "llama3:latest")
                self.assertEqual(model1.provider, "ollama")
                
                # Test with provider inference
                model2 = manager.get_model_info("microsoft/phi-3-mini")
                self.assertIsNotNone(model2)
                self.assertEqual(model2.provider, "huggingface")
    
    def test_filter_models(self):
        """Test filtering models by criteria."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                
                # Force cache refresh
                manager._refresh_cache(force=True)
                
                # Filter by capability
                vision_models = manager.filter_models(capabilities=["image"])
                self.assertEqual(len(vision_models), 3)
                
                # Filter by provider
                hf_models = manager.filter_models(providers=["huggingface"])
                self.assertEqual(len(hf_models), 3)
                
                # Filter by tag
                large_models = manager.filter_models(tags=["large"])
                self.assertEqual(len(large_models), 2)
                
                # Filter by size
                small_models = manager.filter_models(max_size_mb=2000)
                self.assertEqual(len(small_models), 1)
                
                # Filter by installed status
                installed = manager.filter_models(installed_only=True)
                self.assertEqual(len(installed), 2)
    
    def test_get_best_model_for_task(self):
        """Test getting best model for a task."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                
                # Force cache refresh
                manager._refresh_cache(force=True)
                
                # Test getting best text model
                text_model = manager.get_best_model_for_task("text")
                self.assertIsNotNone(text_model)
                
                # Test getting best vision model
                vision_model = manager.get_best_model_for_task("image")
                self.assertIsNotNone(vision_model)
                
                # Test with provider preference
                hf_vision_model = manager.get_best_model_for_task("image", prefer_provider="huggingface")
                self.assertIsNotNone(hf_vision_model)
                self.assertTrue("huggingface/" in hf_vision_model)
    
    def test_model_operations(self):
        """Test model operations (download, load, unload)."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                manager.offline_mode = False
                
                # Force cache refresh
                manager._refresh_cache(force=True)
                
                # Test downloading a model
                self.assertTrue(manager.download_model("huggingface/Salesforce/blip2-opt-2.7b"))
                
                # Test loading a model
                self.assertTrue(manager.load_model("ollama/llama3:latest"))
                
                # Test unloading a model
                self.assertTrue(manager.unload_model("ollama/llama3:latest"))
    
    def test_provider_inference(self):
        """Test provider inference from model name."""
        with patch.dict("multimodal.models.unified_manager.logging.Logger.manager.loggerDict", {}):
            with patch.object(UnifiedModelManager, "__init__", return_value=None):
                manager = UnifiedModelManager()
                manager.managers = {
                    "ollama": self.ollama_manager,
                    "huggingface": self.hf_manager
                }
                manager.active_providers = ["ollama", "huggingface"]
                manager.available_providers = ["ollama", "huggingface"]
                manager._model_cache = {}
                manager._last_refresh = 0
                manager._cache_ttl = 0
                manager.config = MagicMock()
                
                # Test Ollama style model name
                provider1 = manager.get_provider_for_model("llama3:latest")
                self.assertEqual(provider1, "ollama")
                
                # Test Hugging Face style model name
                provider2 = manager.get_provider_for_model("microsoft/phi-3-mini")
                self.assertEqual(provider2, "huggingface")


if __name__ == "__main__":
    unittest.main()
