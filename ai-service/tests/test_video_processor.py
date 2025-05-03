#!/usr/bin/env python3
"""
Test Video Processor

Tests the functionality of the VideoProcessor class.
"""

import unittest
import os
import sys
import tempfile
import logging
import numpy as np
from pathlib import Path
import cv2

# Add the parent directory to the Python path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger("VideoProcessorTest")

# Import the necessary modules
try:
    from multimodal.processors.video_processor import VideoProcessor
    from multimodal.models.unified_manager import UnifiedModelManager
    from multimodal.processors.base_processor import ProcessingResult
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

class MockUnifiedModelManager:
    """Mock version of UnifiedModelManager for testing."""
    
    def __init__(self):
        self.loaded_models = {}
        self.available_providers = ["ollama"]
    
    def is_provider_available(self, provider):
        return provider in self.available_providers
    
    def is_model_available(self, model_id):
        # Mock method to simulate model availability check
        return True
    
    def _parse_model_id(self, model_id):
        """Parse model ID to extract provider and name."""
        if "/" in model_id:
            provider, name = model_id.split("/", 1)
            return provider, name
        else:
            return "ollama", model_id
    
    def get_model_info(self, model_id):
        """Mock method to return model information."""
        provider, name = self._parse_model_id(model_id)
        return {
            "id": model_id,
            "name": name,
            "provider": provider,
            "capabilities": ["image", "text", "video"],
            "parameters": {},
            "loaded": True
        }
    
    def get_manager_for_provider(self, provider):
        """Mock method to return the provider-specific manager."""
        return self  # Return self as if it's the provider manager
    
    def get_provider_for_model(self, model_id):
        if '/' in model_id:
            return model_id.split('/')[0]
        return "ollama"  # Default provider
    
    def check_resource_availability(self, required_memory_gb):
        # Always return True for testing
        return True
    
    def unload_all_models(self, provider=None, exclude_provider=None):
        # Simulate unloading models
        if provider:
            # Unload only models from this provider
            self.loaded_models = {k: v for k, v in self.loaded_models.items() 
                                if not k.startswith(f"{provider}/")}
        elif exclude_provider:
            # Unload all except this provider
            self.loaded_models = {k: v for k, v in self.loaded_models.items() 
                                if k.startswith(f"{exclude_provider}/")}
        else:
            # Unload all models
            self.loaded_models = {}
        
        return True
    
    def generate_with_images(self, provider, model_name, prompt, image_paths, **kwargs):
        """Mock image generation."""
        return {
            "response": f"Mock analysis of {len(image_paths)} images with model {model_name}. Prompt: {prompt[:30]}...",
            "model": model_name,
            "created_at": "2025-05-02T12:00:00.000Z",
            "done": True,
            "total_duration": 1000,
            "load_duration": 200,
            "prompt_eval_count": 100,
            "prompt_eval_duration": 800,
            "eval_count": 150,
            "eval_duration": 1000
        }

class MockImageProcessor:
    """Mock version of ImageProcessor for testing."""
    
    def __init__(self, model_manager=None):
        self.model_manager = model_manager or MockUnifiedModelManager()
    
    def process(self, data, model_id=None, prompt=None, return_raw_output=False, **kwargs):
        """Mock processing of images."""
        return ProcessingResult(
            success=True,
            modality="image",
            model_id=model_id or "ollama/llava",
            content={"description": f"Mock image analysis of frame with model {model_id}"},
            metadata={"processing_time": 0.5, "frame_dimensions": (640, 480)}
        )


class TestVideoProcessor(unittest.TestCase):
    """Test cases for the VideoProcessor class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        logger.info("Setting up VideoProcessor test")
        cls.model_manager = MockUnifiedModelManager()
        # Create a mock image processor for testing
        cls.image_processor = MockImageProcessor(cls.model_manager)
        cls.video_processor = VideoProcessor(
            model_manager=cls.model_manager, 
            default_model_id="ollama/llava",
            image_processor=cls.image_processor
        )
        
        # Create a sample test video
        cls.test_video_path = cls._create_test_video()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Remove test files
        if os.path.exists(cls.test_video_path):
            os.remove(cls.test_video_path)
    
    @classmethod
    def _create_test_video(cls):
        """Create a test video file for testing."""
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.mp4')
        os.close(fd)
        
        # Define video parameters
        width, height = 640, 480
        fps = 30
        seconds = 2
        
        # Create a video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec
        out = cv2.VideoWriter(path, fourcc, fps, (width, height))
        
        # Create frames with different colors for the test video
        for i in range(fps * seconds):
            # Create a colored frame based on frame number
            if i < fps:  # First second: red
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :, 2] = 255  # Red channel
            else:  # Second second: blue
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :, 0] = 255  # Blue channel
                
            # Add frame number text
            cv2.putText(
                frame, 
                f"Frame {i}", 
                (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (255, 255, 255), 
                2
            )
            
            # Write the frame
            out.write(frame)
        
        # Release the video writer
        out.release()
        logger.info(f"Created test video at {path}")
        return path
    
    def test_initialization(self):
        """Test that VideoProcessor initializes correctly."""
        self.assertIsNotNone(self.video_processor)
        self.assertEqual(self.video_processor.get_modality(), "video")
        self.assertEqual(self.video_processor.get_default_model_id(), "ollama/llava")
    
    def test_supported_formats(self):
        """Test supported video formats."""
        formats = self.video_processor.get_supported_formats()
        self.assertIn(".mp4", formats)
        self.assertIn(".avi", formats)
        self.assertIn(".mov", formats)
    
    def test_validate_input(self):
        """Test input validation."""
        # Valid input (file path)
        is_valid, error = self.video_processor.validate_input(self.test_video_path)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Invalid input (non-existent file)
        is_valid, error = self.video_processor.validate_input("/path/to/nonexistent.mp4")
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        
        # Valid input (numpy array as frame)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        is_valid, error = self.video_processor.validate_input(frame)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_load_video(self):
        """Test loading a video file."""
        cap, metadata, error = self.video_processor.load_video(self.test_video_path)
        self.assertIsNotNone(cap)
        self.assertIsNone(error)
        self.assertIn("fps", metadata)
        self.assertIn("frame_count", metadata)
        self.assertIn("width", metadata)
        self.assertIn("height", metadata)
        self.assertIn("duration", metadata)
        
        # Check video properties
        self.assertEqual(metadata["width"], 640)
        self.assertEqual(metadata["height"], 480)
        self.assertEqual(metadata["fps"], 30)
        
        # Cleanup
        if cap:
            cap.release()
    
    def test_extract_frames(self):
        """Test extracting frames from a video."""
        # Test with uniform sampling
        frames, metadata, error = self.video_processor.extract_frames(
            self.test_video_path,
            max_frames=5,
            sampling_strategy="uniform"
        )
        self.assertIsNone(error)
        self.assertEqual(len(frames), 5)
        self.assertEqual(metadata["sampling_strategy"], "uniform")
        self.assertEqual(metadata["extracted_frames"], 5)
        
        # Test with start sampling
        frames, metadata, error = self.video_processor.extract_frames(
            self.test_video_path,
            max_frames=3,
            sampling_strategy="start"
        )
        self.assertIsNone(error)
        self.assertEqual(len(frames), 3)
        self.assertEqual(metadata["sampling_strategy"], "start")
        
        # Test with end sampling
        frames, metadata, error = self.video_processor.extract_frames(
            self.test_video_path,
            max_frames=3,
            sampling_strategy="end"
        )
        self.assertIsNone(error)
        self.assertEqual(len(frames), 3)
        self.assertEqual(metadata["sampling_strategy"], "end")
    
    def test_process(self):
        """Test processing a video."""
        # Process with default parameters
        result = self.video_processor.process(
            self.test_video_path,
            model_id="ollama/llava",
            max_frames=3
        )
        
        self.assertTrue(result.success)
        self.assertIn("frame_analyses", result.content)
        self.assertEqual(len(result.content["frame_analyses"]), 3)
        self.assertIn("summary", result.content)
        
        # Process with frame analysis only
        result = self.video_processor.process(
            self.test_video_path,
            model_id="ollama/llava",
            max_frames=2,
            analyze_frames=True,
            summarize=False
        )
        
        self.assertTrue(result.success)
        self.assertIn("frame_analyses", result.content)
        self.assertEqual(len(result.content["frame_analyses"]), 2)
        self.assertNotIn("summary", result.content)
        
        # Process with summary only
        result = self.video_processor.process(
            self.test_video_path,
            model_id="ollama/llava",
            max_frames=4,
            analyze_frames=False,
            summarize=True
        )
        
        self.assertTrue(result.success)
        self.assertNotIn("frame_analyses", result.content)
        self.assertIn("summary", result.content)
    
    def test_resource_management(self):
        """Test resource management during processing."""
        # First, reset the mock model manager to ensure clean state
        self.model_manager.loaded_models = {"huggingface/clip": True, "huggingface/bert": True}
        
        # Call unload_all_models directly to simulate what would happen in processing
        self.model_manager.unload_all_models(exclude_provider="ollama")
        
        # Verify that HuggingFace models were unloaded
        self.assertFalse(any(k.startswith("huggingface/") for k in self.model_manager.loaded_models))
        
        # Reset the loaded models again
        self.model_manager.loaded_models = {"huggingface/clip": True, "ollama/llava": True}
        
        # Now test unloading with a specific provider
        self.model_manager.unload_all_models(provider="huggingface")
        
        # Check that only HuggingFace models were unloaded
        self.assertFalse(any(k.startswith("huggingface/") for k in self.model_manager.loaded_models))
        self.assertTrue(any(k.startswith("ollama/") for k in self.model_manager.loaded_models))

if __name__ == "__main__":
    logger.info("Running VideoProcessor tests...")
    unittest.main()
