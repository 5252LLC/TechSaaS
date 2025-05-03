#!/usr/bin/env python3
"""
Hitomi-LangChain Connector

This module provides integration between the Hitomi video extraction system
and the LangChain AI service, with a focus on multimodal processing capabilities.
"""

import os
import sys
import json
import logging
import time
import uuid
import threading
import queue
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import Hitomi wrapper and related components
try:
    # Add video-scraper to path for imports
    video_scraper_path = os.path.abspath(os.path.join(os.path.dirname(parent_dir), "video-scraper"))
    if video_scraper_path not in sys.path:
        sys.path.insert(0, video_scraper_path)
    
    from api.hitomi_wrapper import extract_video, get_job_status, cancel_job, HitomiWrapper
    HITOMI_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Hitomi components: {e}")
    HITOMI_AVAILABLE = False

# Import LangChain components
try:
    from langchain.service import LangChainService
    from multimodal.processors.multimodal_processor import MultimodalProcessor
    from multimodal.processors.base_processor import ProcessingResult
    
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"Error importing LangChain components: {e}")
    LANGCHAIN_AVAILABLE = False

# Additional imports for video processing
try:
    import cv2
    import numpy as np
    from PIL import Image
    import io
    import base64
    
    VIDEO_PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"Error importing video processing components: {e}")
    VIDEO_PROCESSING_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hitomi_langchain_connector")

# Constants
DEFAULT_QUEUE_SIZE = 10
DEFAULT_TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
DEFAULT_FRAME_INTERVAL = 5  # Extract a frame every 5 seconds by default

# Default multimodal model - can be overridden in config
DEFAULT_MULTIMODAL_MODEL = "ollama/llava"

class ProcessingJob:
    """
    Represents a multimodal processing job for video content.
    """
    def __init__(self, url: str, query: Optional[str] = None, extraction_job_id: Optional[str] = None):
        self.job_id = str(uuid.uuid4())
        self.url = url
        self.query = query or ""
        self.extraction_job_id = extraction_job_id
        self.status = "pending"
        self.progress = 0
        self.results = None
        self.error = None
        self.start_time = time.time()
        self.end_time = None
        self.frames = []
        self.transcript = None
        self.summary = None
        self.metadata = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "url": self.url,
            "query": self.query,
            "extraction_job_id": self.extraction_job_id,
            "status": self.status,
            "progress": self.progress,
            "results": self.results,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "frames_count": len(self.frames) if self.frames else 0,
            "has_transcript": self.transcript is not None,
            "has_summary": self.summary is not None,
            "metadata": self.metadata
        }


class HitomiLangChainConnector:
    """
    Connector between Hitomi video extraction and LangChain with multimodal support.
    
    This class provides the integration between video extraction capabilities
    and the multimodal processing features of LangChain, including:
    - Video frame extraction for multimodal analysis
    - Video transcript generation and analysis
    - Background processing queue for asynchronous operations
    - Memory integration for persistent conversation history
    """
    
    def __init__(
        self,
        langchain_service: Optional[LangChainService] = None,
        temp_dir: str = DEFAULT_TEMP_DIR,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        frame_interval: int = DEFAULT_FRAME_INTERVAL,
        multimodal_model_id: Optional[str] = None
    ):
        """
        Initialize the Hitomi-LangChain connector.
        
        Args:
            langchain_service: LangChain service instance
            temp_dir: Directory for temporary files
            queue_size: Maximum size of the processing queue
            frame_interval: Interval (in seconds) between frames to extract
            multimodal_model_id: ID of the multimodal model to use
        """
        # Check for required dependencies
        if not HITOMI_AVAILABLE:
            logger.error("Hitomi components not available. Connector will not function properly.")
        
        if not LANGCHAIN_AVAILABLE:
            logger.error("LangChain components not available. Connector will not function properly.")
        
        if not VIDEO_PROCESSING_AVAILABLE:
            logger.error("Video processing components not available. Frame extraction will not work.")
        
        # Initialize components
        self.temp_dir = temp_dir
        self.frame_interval = frame_interval
        os.makedirs(temp_dir, exist_ok=True)
        
        # Initialize LangChain components
        self.langchain_service = langchain_service
        if not self.langchain_service and LANGCHAIN_AVAILABLE:
            logger.info("Initializing new LangChainService")
            self.langchain_service = LangChainService()
        
        # Initialize multimodal processor with error handling for config issues
        self.multimodal_model_id = multimodal_model_id or DEFAULT_MULTIMODAL_MODEL
        
        if LANGCHAIN_AVAILABLE:
            try:
                # First try to create with the default config
                self.multimodal_processor = MultimodalProcessor(
                    default_model_id=self.multimodal_model_id
                )
            except (AttributeError, Exception) as e:
                logger.warning(f"Error creating MultimodalProcessor with default config: {str(e)}")
                
                # Try to patch the configuration by providing a default model directly
                try:
                    from multimodal.utils.config import get_config
                    config = get_config()
                    
                    # Add default_multimodal_model if missing
                    if not hasattr(config, 'default_multimodal_model'):
                        logger.info(f"Adding default_multimodal_model to config: {self.multimodal_model_id}")
                        config.default_multimodal_model = self.multimodal_model_id
                    
                    # Try again with patched config
                    self.multimodal_processor = MultimodalProcessor(
                        default_model_id=self.multimodal_model_id
                    )
                except Exception as e2:
                    logger.error(f"Failed to create MultimodalProcessor even after patching config: {str(e2)}")
                    # Create a mock processor for testing
                    self.multimodal_processor = mock.MagicMock()
                    self.multimodal_processor.process.return_value = type('obj', (object,), {
                        'success': True,
                        'content': {"text": "Mock multimodal processor response."},
                        'metadata': {"processing_time": 0.1}
                    })
        else:
            # Create a mock processor if LangChain is not available
            import mock
            self.multimodal_processor = mock.MagicMock()
            self.multimodal_processor.process.return_value = type('obj', (object,), {
                'success': True,
                'content': {"text": "Mock multimodal processor response."},
                'metadata': {"processing_time": 0.1}
            })
        
        # Initialize Hitomi wrapper
        self.hitomi_wrapper = HitomiWrapper() if HITOMI_AVAILABLE else None
        
        # Initialize job tracking
        self.jobs = {}
        self.job_lock = threading.Lock()
        
        # Initialize processing queue
        self.processing_queue = queue.Queue(maxsize=queue_size)
        self.processing_thread = threading.Thread(target=self._processing_worker, daemon=True)
        self.processing_thread.start()
        
        logger.info(f"Initialized HitomiLangChainConnector with temp_dir={temp_dir}")
    
    def _processing_worker(self):
        """
        Background worker thread for processing queued jobs.
        """
        logger.info("Starting processing worker thread")
        while True:
            try:
                # Get job from queue
                job_id = self.processing_queue.get()
                
                # Skip if job no longer exists
                if job_id not in self.jobs:
                    logger.warning(f"Job {job_id} not found in jobs dict, skipping")
                    self.processing_queue.task_done()
                    continue
                
                # Process job
                logger.info(f"Processing job {job_id}")
                job = self.jobs[job_id]
                
                try:
                    self._process_job(job)
                except Exception as e:
                    logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
                    with self.job_lock:
                        job.status = "error"
                        job.error = str(e)
                        job.end_time = time.time()
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in processing worker: {str(e)}", exc_info=True)
                time.sleep(1)  # Prevent tight loop in case of errors
    
    def _process_job(self, job: ProcessingJob):
        """
        Process a video analysis job.
        
        This method handles:
        1. Video extraction using Hitomi
        2. Frame extraction from the video
        3. Multimodal processing of frames with LangChain
        4. Result compilation and memory storage
        
        Args:
            job: Job to process
        """
        with self.job_lock:
            job.status = "processing"
        
        # Step 1: Extract video if needed
        video_path = self._extract_video(job)
        if not video_path:
            with self.job_lock:
                job.status = "error"
                job.error = "Failed to extract video"
                job.end_time = time.time()
            return
        
        # Step 2: Extract frames
        job.frames = self._extract_frames(video_path, job)
        if not job.frames:
            with self.job_lock:
                job.status = "error"
                job.error = "Failed to extract frames from video"
                job.end_time = time.time()
            return
        
        # Step 3: Process frames with multimodal processor
        with self.job_lock:
            job.status = "analyzing"
            job.progress = 50
        
        # Process text + video query
        if job.query:
            results = self._process_frames_with_query(job.frames, job.query, job)
        else:
            # Generate basic description without specific query
            results = self._process_frames_for_description(job.frames, job)
        
        # Step 4: Compile results
        with self.job_lock:
            job.results = results
            job.status = "completed"
            job.progress = 100
            job.end_time = time.time()
            
            # Save results to memory if LangChain service is available
            if self.langchain_service and hasattr(self.langchain_service, 'memory_manager'):
                memory_key = f"video_analysis_{job.job_id}"
                self.langchain_service.memory_manager.add_message(
                    memory_key, 
                    f"Video Analysis Request: {job.url} - {job.query if job.query else 'No specific query'}",
                    role="human"
                )
                self.langchain_service.memory_manager.add_message(
                    memory_key,
                    f"Video Analysis Result: {json.dumps(results, indent=2)}",
                    role="ai"
                )
        
        logger.info(f"Completed processing job {job.job_id}")
    
    def _extract_video(self, job: ProcessingJob) -> Optional[str]:
        """
        Extract video using Hitomi wrapper.
        
        Args:
            job: Processing job
            
        Returns:
            Path to extracted video or None if extraction failed
        """
        # Check if we already have an extraction job ID
        if job.extraction_job_id:
            # Check status of existing job
            extraction_status = get_job_status(job.extraction_job_id)
            if not extraction_status:
                logger.error(f"Extraction job {job.extraction_job_id} not found")
                return None
                
            if extraction_status.get("status") == "completed":
                return extraction_status.get("output_path")
                
            elif extraction_status.get("status") == "error":
                logger.error(f"Extraction job failed: {extraction_status.get('error')}")
                return None
                
            else:
                # Job still in progress, wait a bit
                logger.info(f"Extraction job {job.extraction_job_id} still in progress, waiting...")
                max_wait = 30  # Maximum wait time in seconds
                wait_time = 0
                while wait_time < max_wait:
                    time.sleep(5)
                    wait_time += 5
                    
                    extraction_status = get_job_status(job.extraction_job_id)
                    if not extraction_status:
                        break
                        
                    if extraction_status.get("status") == "completed":
                        return extraction_status.get("output_path")
                        
                    elif extraction_status.get("status") == "error":
                        logger.error(f"Extraction job failed: {extraction_status.get('error')}")
                        return None
                
                logger.error(f"Timed out waiting for extraction job {job.extraction_job_id}")
                return None
        
        # Start a new extraction job
        try:
            if not HITOMI_AVAILABLE:
                logger.error("Hitomi components not available, cannot extract video")
                return None
                
            logger.info(f"Starting video extraction for {job.url}")
            extraction_result = extract_video(job.url)
            
            if not extraction_result or "job_id" not in extraction_result:
                logger.error(f"Failed to start extraction job for {job.url}")
                return None
                
            job.extraction_job_id = extraction_result["job_id"]
            
            # Wait for extraction to complete
            max_wait = 300  # Maximum wait time in seconds
            wait_time = 0
            while wait_time < max_wait:
                time.sleep(5)
                wait_time += 5
                
                extraction_status = get_job_status(job.extraction_job_id)
                if not extraction_status:
                    continue
                    
                if extraction_status.get("status") == "completed":
                    return extraction_status.get("output_path")
                    
                elif extraction_status.get("status") == "error":
                    logger.error(f"Extraction job failed: {extraction_status.get('error')}")
                    return None
            
            logger.error(f"Timed out waiting for extraction job {job.extraction_job_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting video: {str(e)}", exc_info=True)
            return None
    
    def _extract_frames(self, video_path: str, job: ProcessingJob) -> List[Dict[str, Any]]:
        """
        Extract frames from a video file.
        
        Args:
            video_path: Path to the video file
            job: Processing job
            
        Returns:
            List of extracted frames with metadata
        """
        if not VIDEO_PROCESSING_AVAILABLE:
            logger.error("Video processing components not available, cannot extract frames")
            return []
            
        try:
            # Open video file
            video = cv2.VideoCapture(video_path)
            if not video.isOpened():
                logger.error(f"Failed to open video file: {video_path}")
                return []
                
            # Get video properties
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Calculate frame interval in frames
            frame_interval_frames = int(fps * self.frame_interval)
            if frame_interval_frames <= 0:
                frame_interval_frames = 1
                
            # Extract frames
            frames = []
            frame_number = 0
            while True:
                # Read frame
                ret, frame = video.read()
                if not ret:
                    break
                    
                # Extract frame at intervals
                if frame_number % frame_interval_frames == 0:
                    # Convert frame to JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    
                    # Calculate timestamp
                    timestamp = frame_number / fps if fps > 0 else 0
                    
                    # Add frame to list
                    frames.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "timestamp_str": self._format_timestamp(timestamp),
                        "image_data": jpg_as_text,
                        "width": frame.shape[1],
                        "height": frame.shape[0]
                    })
                    
                    # Update progress
                    progress = int((frame_number / frame_count) * 40) + 10
                    with self.job_lock:
                        job.progress = min(progress, 50)
                
                frame_number += 1
                
            # Release video
            video.release()
            
            logger.info(f"Extracted {len(frames)} frames from {video_path}")
            return frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}", exc_info=True)
            return []
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _process_frames_with_query(
        self, 
        frames: List[Dict[str, Any]], 
        query: str,
        job: ProcessingJob
    ) -> Dict[str, Any]:
        """
        Process frames with a specific query using multimodal processor.
        
        Args:
            frames: List of extracted frames
            query: User query about the video
            job: Processing job
            
        Returns:
            Processed results
        """
        if not frames:
            return {"error": "No frames to process"}
            
        try:
            # Select representative frames (first, middle, last and some in between)
            if len(frames) > 5:
                # Select first, last, and 3 evenly spaced frames in between
                indices = [0, len(frames) // 4, len(frames) // 2, (3 * len(frames)) // 4, len(frames) - 1]
                selected_frames = [frames[i] for i in indices]
            else:
                selected_frames = frames
                
            results = []
            # Process each frame with the query
            for i, frame in enumerate(selected_frames):
                # Decode image data
                image_data = base64.b64decode(frame["image_data"])
                
                # Process with multimodal processor
                processing_input = {
                    "text": query,
                    "image": image_data
                }
                
                processing_result = self.multimodal_processor.process(
                    processing_input,
                    model_id=self.multimodal_model_id
                )
                
                if processing_result.success:
                    # Add frame metadata to result
                    result = {
                        "frame_number": frame["frame_number"],
                        "timestamp": frame["timestamp"],
                        "timestamp_str": frame["timestamp_str"],
                        "analysis": processing_result.content
                    }
                    results.append(result)
                    
                # Update progress
                progress = int((i / len(selected_frames)) * 40) + 50
                with self.job_lock:
                    job.progress = min(progress, 90)
            
            # Compile final results
            final_results = {
                "query": query,
                "frame_analyses": results,
                "summary": self._generate_summary(results, query, job)
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error processing frames with query: {str(e)}", exc_info=True)
            return {"error": f"Error processing frames: {str(e)}"}
    
    def _process_frames_for_description(
        self, 
        frames: List[Dict[str, Any]],
        job: ProcessingJob
    ) -> Dict[str, Any]:
        """
        Process frames to generate a general description without a specific query.
        
        Args:
            frames: List of extracted frames
            job: Processing job
            
        Returns:
            Processed results with general description
        """
        if not frames:
            return {"error": "No frames to process"}
            
        try:
            # Select representative frames (first, middle, last)
            if len(frames) > 3:
                # Select first, middle, and last frames
                indices = [0, len(frames) // 2, len(frames) - 1]
                selected_frames = [frames[i] for i in indices]
            else:
                selected_frames = frames
                
            results = []
            # Process each frame
            for i, frame in enumerate(selected_frames):
                # Decode image data
                image_data = base64.b64decode(frame["image_data"])
                
                # Process with multimodal processor
                processing_input = {
                    "text": "Describe this image in detail.",
                    "image": image_data
                }
                
                processing_result = self.multimodal_processor.process(
                    processing_input,
                    model_id=self.multimodal_model_id
                )
                
                if processing_result.success:
                    # Add frame metadata to result
                    result = {
                        "frame_number": frame["frame_number"],
                        "timestamp": frame["timestamp"],
                        "timestamp_str": frame["timestamp_str"],
                        "description": processing_result.content.get("text", "")
                    }
                    results.append(result)
                    
                # Update progress
                progress = int((i / len(selected_frames)) * 40) + 50
                with self.job_lock:
                    job.progress = min(progress, 90)
            
            # Compile final results
            final_results = {
                "frame_descriptions": results,
                "summary": self._generate_summary(results, "Describe the content of this video.", job)
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error processing frames for description: {str(e)}", exc_info=True)
            return {"error": f"Error processing frames: {str(e)}"}
    
    def _generate_summary(
        self,
        frame_results: List[Dict[str, Any]],
        query: str,
        job: ProcessingJob
    ) -> str:
        """
        Generate a summary of frame analysis results using LangChain.
        
        Args:
            frame_results: Results from frame analysis
            query: Original query or instruction
            job: Processing job
            
        Returns:
            Summary text
        """
        if not self.langchain_service:
            return "LangChain service not available for summary generation."
            
        try:
            # Prepare input for summary generation
            summaries = []
            for result in frame_results:
                timestamp = result.get("timestamp_str", "")
                if "analysis" in result:
                    content = result.get("analysis", {}).get("text", "")
                elif "description" in result:
                    content = result.get("description", "")
                else:
                    content = "No content available"
                    
                summaries.append(f"[{timestamp}]: {content}")
                
            summary_input = "\n\n".join(summaries)
            
            # Generate summary using LangChain
            prompt = f"""
            You are analyzing a video. Below are descriptions/analyses of frames from the video at different timestamps.
            
            Original query: {query}
            
            Frame information:
            {summary_input}
            
            Based on the above information, provide a comprehensive summary of the video content.
            Focus on the main elements, any temporal progression, and directly address the original query if present.
            """
            
            memory_key = f"video_summary_{job.job_id}"
            
            # Generate response
            summary = self.langchain_service.generate_response(
                input_text=prompt,
                memory_key=memory_key,
                system_message="You are a video analysis assistant that provides clear, concise summaries of video content."
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}", exc_info=True)
            return f"Error generating summary: {str(e)}"
    
    def submit_video_analysis_job(
        self, 
        url: str, 
        query: Optional[str] = None,
        extraction_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a video analysis job.
        
        Args:
            url: URL of the video to analyze
            query: Optional query about the video
            extraction_job_id: Optional ID of an existing extraction job
            
        Returns:
            Dictionary with job details
        """
        # Create a new job
        job = ProcessingJob(url, query, extraction_job_id)
        
        # Store job in jobs dict
        with self.job_lock:
            self.jobs[job.job_id] = job
        
        # Add to processing queue
        try:
            self.processing_queue.put(job.job_id, block=False)
        except queue.Full:
            logger.warning(f"Processing queue is full. Job {job.job_id} will be processed later.")
            
        # Create job info
        job_info = {
            "job_id": job.job_id,
            "url": job.url,
            "query": job.query,
            "status": job.status,
            "timestamp": job.start_time,
            "timestamp_str": self._format_timestamp(job.start_time)
        }
        
        # For demo purposes, if Hitomi is not available, create mock results after a delay
        if not HITOMI_AVAILABLE:
            logger.warning("Hitomi components not available, creating mock results for demo purposes")
            
            # Capture job_id in closure to avoid UnboundLocalError
            job_id = job.job_id
            
            def create_mock_results(job_id=job_id):
                time.sleep(3)  # Wait to simulate processing
                
                # Create mock frames
                mock_frames = []
                for i in range(3):
                    try:
                        # Create a simple colored image as base64
                        img = np.ones((360, 640, 3), dtype=np.uint8)
                        if i == 0:
                            img[:, :] = (255, 0, 0)  # Red
                        elif i == 1:
                            img[:, :] = (0, 255, 0)  # Green
                        else:
                            img[:, :] = (0, 0, 255)  # Blue
                            
                        # Convert to base64
                        _, buffer = cv2.imencode('.jpg', img)
                        img_str = base64.b64encode(buffer).decode('utf-8')
                        
                        mock_frames.append({
                            "frame_number": i * 30,
                            "timestamp": i * 1.0,
                            "timestamp_str": f"00:00:0{i}",
                            "image_data": img_str,
                            "width": 640,
                            "height": 360
                        })
                    except Exception as e:
                        logger.error(f"Error creating mock frame: {e}")
                        # Create a simple placeholder base64 image if OpenCV fails
                        img_str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQI12P4//8/AAX+Av7czFnnAAAAAElFTkSuQmCC"
                        mock_frames.append({
                            "frame_number": i * 30,
                            "timestamp": i * 1.0,
                            "timestamp_str": f"00:00:0{i}",
                            "image_data": img_str,
                            "width": 640,
                            "height": 360
                        })
                
                # Create mock results
                with self.job_lock:
                    if job_id in self.jobs:
                        current_job = self.jobs[job_id]
                        current_job.status = "completed"
                        current_job.frames = mock_frames
                        
                        # Create mock results
                        if current_job.query:
                            frame_analyses = []
                            for i, frame in enumerate(mock_frames):
                                frame_analyses.append({
                                    "frame_number": frame["frame_number"],
                                    "timestamp": frame["timestamp"],
                                    "timestamp_str": frame["timestamp_str"],
                                    "image_data": frame["image_data"],
                                    "text": f"Mock analysis of frame {i}: This appears to be {'a red' if i == 0 else 'a green' if i == 1 else 'a blue'} frame."
                                })
                                
                            current_job.results = {
                                "query": current_job.query,
                                "frame_analyses": frame_analyses,
                                "summary": f"Mock video analysis for URL: {current_job.url}\n\nThis video contains 3 frames of different colors. The query was: '{current_job.query}'. In a real implementation, this would show AI-generated analysis of the video content."
                            }
                        else:
                            frame_descriptions = []
                            for i, frame in enumerate(mock_frames):
                                frame_descriptions.append({
                                    "frame_number": frame["frame_number"],
                                    "timestamp": frame["timestamp"],
                                    "timestamp_str": frame["timestamp_str"],
                                    "image_data": frame["image_data"],
                                    "description": f"{'A red frame' if i == 0 else 'A green frame' if i == 1 else 'A blue frame'}"
                                })
                                
                            current_job.results = {
                                "frame_descriptions": frame_descriptions,
                                "summary": f"Mock video description for URL: {current_job.url}\n\nThis video contains 3 frames of different colors (red, green, and blue). In a real implementation, this would show AI-generated description of the video content."
                            }
                        
                        logger.info(f"Created mock results for job {job_id}")
                    else:
                        logger.error(f"Job {job_id} not found when creating mock results")
            
            # Start a thread to create mock results
            threading.Thread(target=create_mock_results, daemon=True).start()
        
        return job_info

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a job.
        
        Args:
            job_id: ID of the job to check
            
        Returns:
            Dictionary with job details or None if job not found
        """
        with self.job_lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
                
            return job.to_dict()
    
    def get_frame_preview(self, job_id: str, frame_number: int) -> Optional[str]:
        """
        Get a preview image for a specific frame.
        
        Args:
            job_id: ID of the job
            frame_number: Number of the frame to preview
            
        Returns:
            Base64-encoded preview image or None if not available
        """
        with self.job_lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
                
            # Find the frame
            for frame in job.frames:
                if frame.get("frame_number") == frame_number:
                    return frame.get("image_data")
                    
            return None
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        Get a list of all jobs.
        
        Returns:
            List of job details
        """
        with self.job_lock:
            return [job.to_dict() for job in self.jobs.values()]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if job was cancelled, False otherwise
        """
        with self.job_lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
                
            # Cancel extraction job if it exists
            if job.extraction_job_id:
                try:
                    cancel_job(job.extraction_job_id)
                except Exception as e:
                    logger.error(f"Error cancelling extraction job: {str(e)}")
                    
            # Update job status
            job.status = "cancelled"
            job.end_time = time.time()
            
            return True
    
    def cleanup_job(self, job_id: str) -> bool:
        """
        Clean up resources associated with a job.
        
        Args:
            job_id: ID of the job to clean up
            
        Returns:
            True if job was cleaned up, False otherwise
        """
        with self.job_lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
                
            # Remove job from jobs dict
            del self.jobs[job_id]
            
            return True


# Example usage
if __name__ == "__main__":
    # Initialize connector
    connector = HitomiLangChainConnector()
    
    # Submit a job
    job = connector.submit_video_analysis_job(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        query="What is the main subject of this video?"
    )
    
    print(f"Submitted job: {job['job_id']}")
    
    # Wait for job to complete
    while True:
        status = connector.get_job_status(job['job_id'])
        if status['status'] in ['completed', 'error']:
            break
        print(f"Job status: {status['status']}, progress: {status['progress']}%")
        time.sleep(5)
    
    # Print results
    print(f"Job completed with status: {status['status']}")
    if status['status'] == 'completed':
        print(f"Summary: {status['results']['summary']}")
