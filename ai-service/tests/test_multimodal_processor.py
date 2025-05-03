#!/usr/bin/env python3
"""
Tests for Multimodal Processor System

This module contains unit tests for the processor system,
which handles different types of modalities and their processing.
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
from multimodal.processors.base_processor import BaseProcessor, ProcessingResult
from multimodal.processors.processor_factory import ProcessorFactory
from multimodal.processors.image_processor import ImageProcessor
from multimodal.processors.text_processor import TextProcessor
from multimodal.processors.multimodal_processor import MultimodalProcessor
from multimodal.models.unified_manager import UnifiedModelManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultimodalProcessorTest")


class MockUnifiedModelManager(MagicMock):
    """Mock model manager for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.models = {
            "ollama/llama3:latest": {
                "name": "llama3:latest",
                "provider": "ollama",
                "capabilities": ["text"],
                "min_ram_gb": 2.0,
                "loaded": False
            },
            "ollama/phi-vision:latest": {
                "name": "phi-vision:latest",
                "provider": "ollama",
                "capabilities": ["image", "text"],
                "min_ram_gb": 4.0,
                "loaded": False
            },
            "huggingface/microsoft/phi-3-mini": {
                "name": "microsoft/phi-3-mini",
                "provider": "huggingface",
                "capabilities": ["text"],
                "min_ram_gb": 2.0,
                "loaded": False
            },
            "huggingface/llava-hf/llava-1.5-7b-hf": {
                "name": "llava-hf/llava-1.5-7b-hf",
                "provider": "huggingface",
                "capabilities": ["image", "text"],
                "min_ram_gb": 8.0,
                "loaded": False
            }
        }
        self.loaded_models = set()
    
    def get_model_info(self, model_id):
        """Get info for a specific model."""
        model_data = self.models.get(model_id)
        if model_data:
            model_info = MagicMock()
            model_info.name = model_data["name"]
            model_info.provider = model_data["provider"]
            model_info.capabilities = model_data["capabilities"]
            model_info.min_ram_gb = model_data["min_ram_gb"]
            model_info.loaded = model_id in self.loaded_models
            return model_info
        return None
    
    def is_model_available(self, model_id):
        """Check if model is available."""
        return model_id in self.models
    
    def get_provider_for_model(self, model_id):
        """Get provider for model."""
        if model_id in self.models:
            return self.models[model_id]["provider"]
        
        # Try to infer provider from model name format
        if "/" in model_id:
            org, _ = model_id.split("/", 1)
            return "huggingface"
        elif ":" in model_id:
            return "ollama"
        
        return None
    
    def _parse_model_id(self, model_id):
        """Parse a model ID into provider and name."""
        if "/" in model_id:
            provider, name = model_id.split("/", 1)
            return provider, name
        return None, model_id
    
    def ensure_model_availability(self, model_id):
        """Ensure model is available."""
        return model_id in self.models
    
    def list_active_providers(self):
        """List active providers."""
        return ["ollama", "huggingface"]
    
    def check_resource_availability(self, required_memory_gb):
        """Mock resource availability check."""
        # Always return True in tests
        return True
    
    def unload_all_models(self, provider=None):
        """Mock unloading all models."""
        if provider:
            # Unload models from specific provider
            self.loaded_models = {
                model_id for model_id in self.loaded_models
                if self.models[model_id]["provider"] != provider
            }
        else:
            # Unload all models
            self.loaded_models = set()
        
        return True
    
    def load_model(self, model_id):
        """Mock loading a model."""
        if model_id in self.models:
            self.loaded_models.add(model_id)
            return True
        return False
    
    def unload_model(self, model_id):
        """Mock unloading a model."""
        if model_id in self.loaded_models:
            self.loaded_models.remove(model_id)
            return True
        return False


class TestProcessorBase(unittest.TestCase):
    """Base class for processor tests."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock model manager
        self.model_manager = MockUnifiedModelManager()
        
        # Set up patches
        self.patches = [
            patch("multimodal.utils.config.get_config", return_value=self._mock_config()),
            patch("PIL.Image.open", return_value=self._mock_image()),
            patch("numpy.array", return_value=self._mock_array()),
            patch("cv2.imread", return_value=self._mock_array()),
            patch("cv2.cvtColor", return_value=self._mock_array()),
            patch("cv2.resize", return_value=self._mock_array()),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
            patch("builtins.open", self._mock_open()),
            patch("httpx.post", return_value=self._mock_response())
        ]
        
        # Start patches
        for p in self.patches:
            p.start()
    
    def tearDown(self):
        """Clean up after tests."""
        # Stop patches
        for p in self.patches:
            p.stop()
    
    def _mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.default_image_model = "ollama/phi-vision:latest"
        config.default_text_model = "ollama/llama3:latest"
        config.default_multimodal_model = "ollama/phi-vision:latest"
        config.processing.max_text_length = 10000
        config.processing.max_file_size_mb = 10
        config.adapt_to_hardware = True
        return config
    
    def _mock_image(self):
        """Create mock PIL image."""
        img = MagicMock()
        img.convert.return_value = img
        return img
    
    def _mock_array(self):
        """Create mock numpy array."""
        arr = MagicMock()
        arr.shape = (224, 224, 3)
        return arr
    
    def _mock_open(self):
        """Create mock file handler."""
        mock_file = MagicMock()
        mock_file.read.return_value = "test content"
        
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        return mock_open
    
    def _mock_response(self):
        """Create mock HTTP response."""
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "response": "This is a test response.",
            "model": "test-model"
        }
        return response


class TestProcessorFactory(TestProcessorBase):
    """Test the processor factory system."""
    
    def test_factory_initialization(self):
        """Test initializing the processor factory."""
        factory = ProcessorFactory(self.model_manager)
        self.assertIsInstance(factory, ProcessorFactory)
    
    def test_processor_registration(self):
        """Test registering processors with the factory."""
        factory = ProcessorFactory(self.model_manager)
        
        # Create and register processors
        image_processor = ImageProcessor(self.model_manager)
        text_processor = TextProcessor(self.model_manager)
        multimodal_processor = MultimodalProcessor(self.model_manager)
        
        factory.register_processor(image_processor)
        factory.register_processor(text_processor)
        factory.register_processor(multimodal_processor)
        
        # Check registration
        self.assertEqual(factory.get_processor("image"), image_processor)
        self.assertEqual(factory.get_processor("text"), text_processor)
        self.assertEqual(factory.get_processor("multimodal"), multimodal_processor)
        
        # Check modality list
        modalities = factory.get_supported_modalities()
        self.assertIn("image", modalities)
        self.assertIn("text", modalities)
        self.assertIn("multimodal", modalities)
    
    def test_processor_selection(self):
        """Test selecting appropriate processor for different inputs."""
        factory = ProcessorFactory(self.model_manager)
        
        # Create and register processors
        image_processor = ImageProcessor(self.model_manager)
        text_processor = TextProcessor(self.model_manager)
        multimodal_processor = MultimodalProcessor(self.model_manager)
        
        factory.register_processor(image_processor)
        factory.register_processor(text_processor)
        factory.register_processor(multimodal_processor)
        
        # Test text input
        processor = factory.get_processor_for_input("Hello, world!")
        self.assertEqual(processor, text_processor)
        
        # Test file path based on extension
        processor = factory.get_processor_for_file("test.jpg")
        self.assertEqual(processor, image_processor)
        
        processor = factory.get_processor_for_file("test.txt")
        self.assertEqual(processor, text_processor)
        
        # Test dictionary with multiple modalities
        processor = factory.get_processor_for_input({
            "text": "Describe this image",
            "image": "test.jpg"
        })
        self.assertEqual(processor, multimodal_processor)
    
    def test_processing_pipeline(self):
        """Test the entire processing pipeline through the factory."""
        factory = ProcessorFactory(self.model_manager)
        
        # Create and register processors
        image_processor = ImageProcessor(self.model_manager)
        text_processor = TextProcessor(self.model_manager)
        multimodal_processor = MultimodalProcessor(self.model_manager)
        
        factory.register_processor(image_processor)
        factory.register_processor(text_processor)
        factory.register_processor(multimodal_processor)
        
        # Test processing text
        result = factory.process("This is a test")
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "text")
        
        # Test processing image
        result = factory.process("test.jpg")
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "image")
        
        # Test processing multimodal
        result = factory.process({
            "text": "Describe this image",
            "image": "test.jpg"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "multimodal")


class TestImageProcessor(TestProcessorBase):
    """Test the image processor."""
    
    def test_initialization(self):
        """Test initializing the image processor."""
        processor = ImageProcessor(self.model_manager)
        self.assertEqual(processor.get_modality(), "image")
        self.assertEqual(processor.get_default_model_id(), "ollama/phi-vision:latest")
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        processor = ImageProcessor(self.model_manager)
        formats = processor.get_supported_formats()
        self.assertIn(".jpg", formats)
        self.assertIn("image/jpeg", formats)
    
    def test_image_processing(self):
        """Test processing an image."""
        processor = ImageProcessor(self.model_manager)
        
        # Test with file path
        result = processor.process("test.jpg")
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "image")
        self.assertIn("description", result.content)
        
        # Test with model specification
        result = processor.process("test.jpg", model_id="ollama/phi-vision:latest")
        self.assertTrue(result.success)
        self.assertEqual(result.model_id, "ollama/phi-vision:latest")


class TestTextProcessor(TestProcessorBase):
    """Test the text processor."""
    
    def test_initialization(self):
        """Test initializing the text processor."""
        processor = TextProcessor(self.model_manager)
        self.assertEqual(processor.get_modality(), "text")
        self.assertEqual(processor.get_default_model_id(), "ollama/llama3:latest")
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        processor = TextProcessor(self.model_manager)
        formats = processor.get_supported_formats()
        self.assertIn(".txt", formats)
        self.assertIn("text/plain", formats)
    
    def test_text_processing(self):
        """Test processing text."""
        processor = TextProcessor(self.model_manager)
        
        # Test with string
        result = processor.process("This is a test")
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "text")
        self.assertIn("text", result.content)
        
        # Test with file path
        result = processor.process("test.txt")
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "text")


class TestMultimodalProcessor(TestProcessorBase):
    """Test the multimodal processor."""
    
    def test_initialization(self):
        """Test initializing the multimodal processor."""
        processor = MultimodalProcessor(self.model_manager)
        self.assertEqual(processor.get_modality(), "multimodal")
        self.assertEqual(processor.get_default_model_id(), "ollama/phi-vision:latest")
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        processor = MultimodalProcessor(self.model_manager)
        formats = processor.get_supported_formats()
        self.assertIn("text+image", formats)
    
    def test_multimodal_processing(self):
        """Test processing multimodal input."""
        processor = MultimodalProcessor(self.model_manager)
        
        # Test with dictionary input
        result = processor.process({
            "text": "Describe this image",
            "image": "test.jpg"
        })
        self.assertTrue(result.success)
        self.assertEqual(result.modality, "multimodal")
        self.assertIn("description", result.content)


if __name__ == "__main__":
    unittest.main()
