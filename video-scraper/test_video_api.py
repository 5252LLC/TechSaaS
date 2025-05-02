#!/usr/bin/env python3
"""
TechSaaS Platform - Video Scraper API Integration Tests
Tests the functionality of the video scraper API endpoints
"""
import unittest
import requests
import os
import json
import time
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoScraperAPITest(unittest.TestCase):
    """Test suite for Video Scraper API"""
    
    BASE_URL = "http://localhost:5501"
    TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Reliable test video
    
    def setUp(self):
        """Verify the API is running before tests"""
        try:
            response = requests.get(f"{self.BASE_URL}/api/status", timeout=2)
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            logger.error(f"API connection failed: {str(e)}")
            logger.error("Please ensure the video scraper API is running on port 5501")
            logger.error("Run: cd /home/fiftytwo/Desktop/52 codes/52TechSaas/video-scraper && python -m api.app")
            sys.exit(1)
            
    def test_api_status(self):
        """Test the API status endpoint"""
        logger.info("Testing API status endpoint")
        response = requests.get(f"{self.BASE_URL}/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['service'], "TechSaaS Video Scraper")
        self.assertEqual(data['status'], "operational")
        logger.info("API status endpoint test passed ✅")
    
    def test_supported_platforms(self):
        """Test listing supported platforms"""
        logger.info("Testing supported platforms endpoint")
        response = requests.get(f"{self.BASE_URL}/api/video-scraper/platforms")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0, "No platforms returned")
        
        # Check expected platforms
        platforms = [p['name'].lower() for p in data if 'name' in p]
        self.assertTrue(any('youtube' in p for p in platforms), "YouTube not found in supported platforms")
        logger.info("Supported platforms endpoint test passed ✅")
    
    def test_video_info_extraction(self):
        """Test video info extraction with sample video"""
        logger.info(f"Testing video info extraction with URL: {self.TEST_VIDEO_URL}")
        payload = {"url": self.TEST_VIDEO_URL}
        
        # Request video info extraction
        response = requests.post(
            f"{self.BASE_URL}/api/video-scraper/info",
            json=payload
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('job_id', data)
        
        # Poll for job completion (max 30 seconds)
        job_id = data['job_id']
        logger.info(f"Extraction job started with ID: {job_id}")
        logger.info("Polling for job completion (timeout: 30 seconds)")
        
        start_time = time.time()
        job_complete = False
        final_status = None
        
        while time.time() - start_time < 30:
            status_response = requests.get(
                f"{self.BASE_URL}/api/video-scraper/job/{job_id}"
            )
            status_data = status_response.json()
            logger.info(f"Job status: {status_data.get('status')}")
            
            if status_data.get('status') in ['completed', 'failed']:
                job_complete = True
                final_status = status_data
                break
                
            time.sleep(1)
            
        self.assertTrue(job_complete, "Job did not complete in time")
        
        # Validate successful completion
        if final_status and final_status.get('status') == 'completed':
            self.assertIn('video_info', final_status)
            video_info = final_status['video_info']
            self.assertIn('title', video_info, "Video title not found")
            self.assertIn('formats', video_info, "Video formats not found")
            logger.info(f"Video title: {video_info.get('title')}")
            logger.info(f"Number of formats: {len(video_info.get('formats', []))}")
            logger.info("Video info extraction test passed ✅")
        else:
            self.fail(f"Video extraction failed: {final_status}")
    
    def test_downloads_listing(self):
        """Test listing available downloads"""
        logger.info("Testing downloads listing endpoint")
        response = requests.get(f"{self.BASE_URL}/api/video-scraper/downloads")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        logger.info(f"Found {len(data)} downloads")
        logger.info("Downloads listing test passed ✅")
        
    def test_download_process(self):
        """Test complete download process"""
        # This is optional as it takes longer and creates files
        # Uncomment if you want to test full download functionality
        """
        logger.info(f"Testing download process with URL: {self.TEST_VIDEO_URL}")
        payload = {
            "url": self.TEST_VIDEO_URL,
            "format_id": "best"
        }
        
        # Start download
        response = requests.post(
            f"{self.BASE_URL}/api/video-scraper/download",
            json=payload
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('download_id', data)
        
        download_id = data['download_id']
        logger.info(f"Download started with ID: {download_id}")
        
        # Poll for download completion (max 60 seconds)
        logger.info("Polling for download completion (timeout: 60 seconds)")
        start_time = time.time()
        download_complete = False
        
        while time.time() - start_time < 60:
            status_response = requests.get(
                f"{self.BASE_URL}/api/video-scraper/status/{download_id}"
            )
            status_data = status_response.json()
            
            if status_data.get('status') == 'completed':
                download_complete = True
                self.assertIn('filename', status_data)
                logger.info(f"Download completed, filename: {status_data.get('filename')}")
                break
            
            if status_data.get('status') == 'failed':
                self.fail(f"Download failed: {status_data.get('error')}")
                
            if status_data.get('progress'):
                progress_percent = int(status_data.get('progress') * 100)
                logger.info(f"Download progress: {progress_percent}%")
                
            time.sleep(2)
            
        self.assertTrue(download_complete, "Download did not complete in time")
        logger.info("Download process test passed ✅")
        """

if __name__ == '__main__':
    print("=== TechSaaS Video Scraper API Integration Tests ===")
    print("Running tests...")
    unittest.main(verbosity=2)
