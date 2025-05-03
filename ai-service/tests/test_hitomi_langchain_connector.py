#!/usr/bin/env python3
"""
Test Hitomi-LangChain Connector

Tests the integration between Hitomi video extraction capabilities and 
LangChain multimodal processing with memory management.
"""

import unittest
import os
import sys
import tempfile
import logging
import json
import shutil
import mock
from pathlib import Path
from typing import Dict, List, Optional, Any
import base64
import time

# Add the parent directory to the Python path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger("HitomiLangChainConnectorTest")

# Import the necessary modules with error handling
try:
    from integration.hitomi_langchain_connector import HitomiLangChainConnector, ProcessingJob
    from langchain.service import LangChainService
    from multimodal.processors.multimodal_processor import MultimodalProcessor
    from multimodal.processors.base_processor import ProcessingResult
    
    CONNECTOR_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    CONNECTOR_AVAILABLE = False


@unittest.skipIf(not CONNECTOR_AVAILABLE, "Hitomi-LangChain connector modules not available")
class TestHitomiLangChainConnector(unittest.TestCase):
    """Test cases for the Hitomi-LangChain connector."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for files
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock LangChain service
        self.langchain_service = mock.MagicMock(spec=LangChainService)
        self.langchain_service.generate_response.return_value = "This is a mock video analysis summary."
        self.langchain_service.memory_manager = mock.MagicMock()
        
        # Create connector with mocked components
        self.connector = HitomiLangChainConnector(
            langchain_service=self.langchain_service,
            temp_dir=self.temp_dir,
            queue_size=5,
            frame_interval=2
        )
        
        # Mock the multimodal processor
        self.connector.multimodal_processor = mock.MagicMock(spec=MultimodalProcessor)
        
        # Mock ProcessingResult with success=True
        mock_result = mock.MagicMock(spec=ProcessingResult)
        mock_result.success = True
        mock_result.content = {"text": "This is a mock analysis of the image."}
        mock_result.metadata = {"processing_time": 0.5}
        
        # Set the return value for the multimodal processor
        self.connector.multimodal_processor.process.return_value = mock_result
        
        # Mock methods that interact with external services
        self.connector._extract_video = mock.MagicMock(return_value=os.path.join(self.temp_dir, "mock_video.mp4"))
        
        # Create sample frame data for testing
        self.sample_frames = [
            {
                "frame_number": 0,
                "timestamp": 0.0,
                "timestamp_str": "00:00:00",
                "image_data": base64.b64encode(b"mock_image_data_1").decode('utf-8'),
                "width": 1280,
                "height": 720
            },
            {
                "frame_number": 30,
                "timestamp": 1.0,
                "timestamp_str": "00:00:01",
                "image_data": base64.b64encode(b"mock_image_data_2").decode('utf-8'),
                "width": 1280,
                "height": 720
            },
            {
                "frame_number": 60,
                "timestamp": 2.0,
                "timestamp_str": "00:00:02",
                "image_data": base64.b64encode(b"mock_image_data_3").decode('utf-8'),
                "width": 1280,
                "height": 720
            }
        ]
        
        # Mock frame extraction
        self.connector._extract_frames = mock.MagicMock(return_value=self.sample_frames)
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_submit_video_analysis_job(self):
        """Test submitting a video analysis job."""
        # Submit a job
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        query = "What is happening in this video?"
        
        job = self.connector.submit_video_analysis_job(url, query)
        
        # Check job was created correctly
        self.assertIsNotNone(job)
        self.assertEqual(job["url"], url)
        self.assertEqual(job["query"], query)
        self.assertEqual(job["status"], "pending")
        
        # Job should be in the jobs dict
        self.assertIn(job["job_id"], self.connector.jobs)
        
        # Check job status
        status = self.connector.get_job_status(job["job_id"])
        self.assertIsNotNone(status)
        self.assertEqual(status["url"], url)
    
    def test_process_frames_with_query(self):
        """Test processing frames with a query."""
        # Create a test job
        job = ProcessingJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            query="What is happening in this video?"
        )
        
        # Process frames
        results = self.connector._process_frames_with_query(
            self.sample_frames,
            job.query,
            job
        )
        
        # Check results
        self.assertIsNotNone(results)
        self.assertIn("query", results)
        self.assertIn("frame_analyses", results)
        self.assertIn("summary", results)
        
        # Should have processed frames
        self.assertEqual(len(results["frame_analyses"]), len(self.sample_frames))
        
        # Multimodal processor should have been called for each frame
        self.assertEqual(
            self.connector.multimodal_processor.process.call_count,
            len(self.sample_frames)
        )
        
        # Check summary was generated
        self.assertEqual(results["summary"], "This is a mock video analysis summary.")
    
    def test_process_frames_for_description(self):
        """Test processing frames for general description."""
        # Create a test job
        job = ProcessingJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        
        # Process frames
        results = self.connector._process_frames_for_description(
            self.sample_frames,
            job
        )
        
        # Check results
        self.assertIsNotNone(results)
        self.assertIn("frame_descriptions", results)
        self.assertIn("summary", results)
        
        # Should have processed frames
        self.assertEqual(len(results["frame_descriptions"]), len(self.sample_frames))
        
        # Multimodal processor should have been called for each frame
        self.assertEqual(
            self.connector.multimodal_processor.process.call_count,
            len(self.sample_frames)
        )
        
        # Check summary was generated
        self.assertEqual(results["summary"], "This is a mock video analysis summary.")
    
    def test_get_frame_preview(self):
        """Test getting a frame preview."""
        # Create a test job
        job = ProcessingJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        
        # Add frames to job
        job.frames = self.sample_frames
        
        # Add job to connector
        with self.connector.job_lock:
            self.connector.jobs[job.job_id] = job
        
        # Get preview for first frame
        preview = self.connector.get_frame_preview(job.job_id, 0)
        self.assertEqual(preview, self.sample_frames[0]["image_data"])
        
        # Get preview for non-existent frame
        preview = self.connector.get_frame_preview(job.job_id, 999)
        self.assertIsNone(preview)
    
    def test_cancel_job(self):
        """Test cancelling a job."""
        # Create a test job
        job = ProcessingJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        
        # Add job to connector
        with self.connector.job_lock:
            self.connector.jobs[job.job_id] = job
        
        # Cancel job
        result = self.connector.cancel_job(job.job_id)
        self.assertTrue(result)
        
        # Check job status
        job_status = self.connector.get_job_status(job.job_id)
        self.assertEqual(job_status["status"], "cancelled")
    
    def test_cleanup_job(self):
        """Test cleaning up a job."""
        # Create a test job
        job = ProcessingJob(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        
        # Add job to connector
        with self.connector.job_lock:
            self.connector.jobs[job.job_id] = job
        
        # Cleanup job
        result = self.connector.cleanup_job(job.job_id)
        self.assertTrue(result)
        
        # Job should be removed
        self.assertNotIn(job.job_id, self.connector.jobs)


if __name__ == "__main__":
    logger.info("Running Hitomi-LangChain connector tests...")
    unittest.main()
