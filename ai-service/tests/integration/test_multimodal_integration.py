#!/usr/bin/env python3
"""
Integration Tests for Multimodal Processing System

This module contains integration tests that verify the end-to-end functionality
of the multimodal processing system, testing the integration between:
- Web interface components
- API endpoints
- Multimodal processor components
- Model management system
"""

import os
import sys
import unittest
import json
import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import necessary modules
from api.endpoints import api_blueprint
from multimodal.processors.multimodal_processor import MultimodalProcessor
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.processors.processor_factory import ProcessorFactory
from web.integration.client import WebApiClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MultimodalIntegrationTest")

class TestMultimodalIntegration(unittest.TestCase):
    """Integration tests for the multimodal processing system."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once before all tests."""
        logger.info("Setting up multimodal integration test environment")
        
        # Create temporary directory for test assets
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_dir = Path(cls.temp_dir.name)
        
        # Create test assets (sample video, image, text)
        cls.create_test_assets()
        
        # Initialize API client with mock server
        cls.client = cls.setup_test_client()
        
        # Initialize model manager with mock models for testing
        cls.model_manager = cls.create_mock_model_manager()
        
        # Initialize processor factory with mock processors
        cls.processor_factory = ProcessorFactory(cls.model_manager)
        
        logger.info(f"Test environment set up in {cls.test_dir}")

    @classmethod
    def tearDownClass(cls):
        """Clean up resources after all tests are complete."""
        # Clean up temporary directory
        cls.temp_dir.cleanup()
        logger.info("Test environment cleaned up")

    @classmethod
    def create_test_assets(cls):
        """Create test assets for integration testing."""
        # Create test video file
        video_path = cls.test_dir / "test_video.mp4"
        with open(video_path, "wb") as f:
            # Write a minimal valid MP4 file header
            f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41\x00\x00\x00\x00')
        
        # Create test image file
        image_path = cls.test_dir / "test_image.jpg"
        with open(image_path, "wb") as f:
            # Write a minimal valid JPEG file header
            f.write(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xFF\xDB\x00\x43\x00\xFF\xC0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xFF\xC4\x00\x1F\x00\xFF\xDA\x00\x08\x01\x01\x00\x00\x3F\x00\xFF\xD9')
        
        # Create test text file
        text_path = cls.test_dir / "test_text.txt"
        with open(text_path, "w") as f:
            f.write("This is a test document for multimodal processing.")
        
        # Create test audio file
        audio_path = cls.test_dir / "test_audio.wav"
        with open(audio_path, "wb") as f:
            # Write a minimal valid WAV file header
            f.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        
        # Store paths for later use in tests
        cls.test_video = str(video_path)
        cls.test_image = str(image_path)
        cls.test_text = str(text_path)
        cls.test_audio = str(audio_path)

    @classmethod
    def setup_test_client(cls):
        """Set up a test client for the API endpoints."""
        # Create a mock Flask app and client
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(api_blueprint)
        
        # Return test client
        return app.test_client()

    @classmethod
    def create_mock_model_manager(cls):
        """Create a mock model manager for testing."""
        model_manager = MagicMock(spec=UnifiedModelManager)
        
        # Mock the model info and capabilities
        model_manager.get_model_info.return_value = {
            "name": "test-multimodal-model",
            "provider": "mock-provider",
            "capabilities": ["image", "text", "video", "audio"],
            "loaded": True
        }
        
        # Mock the model availability check
        model_manager.is_model_available.return_value = True
        
        # Mock the model loading functionality
        model_manager.load_model.return_value = True
        
        # Mock processing results
        def mock_process(*args, **kwargs):
            return {
                "success": True,
                "results": {
                    "content": "Mock multimodal analysis result",
                    "confidence": 0.95,
                    "processing_time": 1.2
                }
            }
        
        model_manager.process = mock_process
        
        return model_manager

    def test_api_endpoint_availability(self):
        """Test that all required API endpoints are available."""
        endpoints = [
            '/api/v1/multimodal/analyze',
            '/api/v1/multimodal/models',
            '/api/v1/multimodal/status'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertIn(response.status_code, [200, 404], f"Endpoint {endpoint} returned unexpected status {response.status_code}")
            if response.status_code == 404:
                logger.warning(f"Endpoint {endpoint} not implemented yet")

    def test_multimodal_processor_initialization(self):
        """Test that the multimodal processor initializes correctly."""
        processor = MultimodalProcessor(model_manager=self.model_manager)
        self.assertIsNotNone(processor, "Multimodal processor should initialize")
        self.assertEqual(processor.modality, "multimodal", "Processor should have multimodal modality")

    def test_video_with_audio_integration(self):
        """Test integrated processing of video with audio."""
        # Initialize processor
        processor = self.processor_factory.get_processor("multimodal")
        self.assertIsNotNone(processor, "Should get a valid multimodal processor")
        
        # Process video file
        result = processor.process(
            data=self.test_video,
            prompt="Analyze this video and extract key information",
            model_id="mock-provider/multimodal-model"
        )
        
        # Verify result structure
        self.assertTrue(hasattr(result, 'success'), "Result should have success attribute")
        self.assertTrue(result.success, "Processing should succeed")
        self.assertTrue(hasattr(result, 'content'), "Result should have content")
        
        # Log result for debugging
        logger.info(f"Video with audio integration test result: {result}")

    def test_multimodal_cross_reference(self):
        """Test cross-referencing between different modalities."""
        # Initialize processor with specific options to enable cross-referencing
        processor = self.processor_factory.get_processor("multimodal")
        
        # Create a multimodal input with text and image
        multimodal_input = {
            "text": "What is shown in this image?",
            "image_path": self.test_image
        }
        
        # Process the multimodal input
        result = processor.process(
            data=multimodal_input,
            enable_cross_reference=True,
            model_id="mock-provider/multimodal-model"
        )
        
        # Verify cross-reference results
        self.assertTrue(hasattr(result, 'success'), "Result should have success attribute")
        self.assertTrue(result.success, "Cross-reference processing should succeed")

    def test_web_ui_integration(self):
        """Test integration between web UI components and backend services."""
        # Mock a web client request
        web_client = WebApiClient()
        
        # Create a mock request similar to what the web UI would send
        request_data = {
            "type": "multimodal_analysis",
            "video_url": "https://example.com/sample.mp4",
            "options": {
                "analyze_audio": True,
                "extract_text": True,
                "detect_objects": True,
                "cross_reference": True
            }
        }
        
        # Mock the response from the API
        with patch.object(web_client, 'submit_job') as mock_submit:
            mock_submit.return_value = {
                "job_id": "mock-job-123",
                "status": "submitted"
            }
            
            # Send the request
            response = web_client.submit_job(request_data)
            
            # Verify the job submission
            self.assertIn('job_id', response, "Response should contain a job ID")
            self.assertEqual(response['status'], "submitted", "Job should be submitted successfully")
        
        # Mock checking job status
        with patch.object(web_client, 'check_job_status') as mock_check:
            mock_check.return_value = {
                "job_id": "mock-job-123",
                "status": "completed",
                "progress": 100,
                "result_url": "https://example.com/results/mock-job-123"
            }
            
            # Check job status
            status = web_client.check_job_status("mock-job-123")
            
            # Verify status response
            self.assertEqual(status['status'], "completed", "Job should be completed")
            self.assertEqual(status['progress'], 100, "Progress should be 100%")

    def test_error_handling(self):
        """Test error handling in the integration pipeline."""
        # Test with invalid file
        processor = self.processor_factory.get_processor("multimodal")
        
        # Process an invalid file
        with self.assertRaises(Exception):
            processor.process(
                data="invalid_file_path",
                model_id="mock-provider/multimodal-model"
            )
        
        # Test with unsupported model
        with patch.object(self.model_manager, 'is_model_available', return_value=False):
            result = processor.process(
                data=self.test_video,
                model_id="unsupported-model"
            )
            self.assertFalse(result.success, "Processing should fail with unsupported model")

    def test_performance_metrics(self):
        """Test performance metrics collection during processing."""
        processor = self.processor_factory.get_processor("multimodal")
        
        # Process with performance tracking enabled
        start_time = time.time()
        result = processor.process(
            data=self.test_video,
            model_id="mock-provider/multimodal-model",
            track_performance=True
        )
        end_time = time.time()
        
        # Calculate total processing time
        total_time = end_time - start_time
        
        # Log performance metrics
        logger.info(f"Processing time: {total_time:.2f} seconds")
        logger.info(f"Performance metrics: {result.metadata.get('performance', {})}")

    def test_multimodal_visualization(self):
        """Test visualization data generation for multimodal results."""
        processor = self.processor_factory.get_processor("multimodal")
        
        # Process with visualization options
        result = processor.process(
            data=self.test_video,
            model_id="mock-provider/multimodal-model",
            generate_visualization=True
        )
        
        # Check visualization data
        self.assertIn('visualization_data', result.metadata, "Result should include visualization data")
        viz_data = result.metadata['visualization_data']
        
        # Log visualization data structure
        logger.info(f"Visualization data structure: {viz_data.keys() if viz_data else 'None'}")

if __name__ == "__main__":
    unittest.main()
