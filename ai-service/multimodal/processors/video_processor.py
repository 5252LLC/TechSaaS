#!/usr/bin/env python3
"""
Video Processor

Implements the BaseProcessor interface for video processing.
Handles loading, frame extraction, and analysis of videos using various models.
"""

import os
import logging
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple, Iterator
import json
from pathlib import Path

# Import optional video processing libraries with graceful fallback
try:
    import numpy as np
    from PIL import Image, UnidentifiedImageError
    import cv2
    VIDEO_PROCESSING_AVAILABLE = True
except ImportError:
    VIDEO_PROCESSING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Video processing libraries not installed, functionality will be limited")

from multimodal.processors.base_processor import BaseProcessor, ProcessingResult
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.processors.image_processor import ImageProcessor

# Configure logging
logger = logging.getLogger(__name__)


class VideoProcessor(BaseProcessor):
    """
    Processor for video data.
    
    This processor handles the loading, frame extraction, and analysis of videos
    using various models from different providers.
    """
    
    def __init__(
            self, 
            model_manager: Optional[UnifiedModelManager] = None,
            default_model_id: Optional[str] = None,
            image_processor: Optional[ImageProcessor] = None
        ):
        """
        Initialize video processor.
        
        Args:
            model_manager: Model manager for accessing models
            default_model_id: Default model ID to use
            image_processor: Optional image processor for frame analysis
        """
        if not VIDEO_PROCESSING_AVAILABLE:
            logger.error("Video processing libraries not installed")
            raise ImportError(
                "Video processing libraries are required. "
                "Install with pip install pillow opencv-python"
            )
        
        from multimodal.utils.config import get_config
        self.config = get_config()
        self.model_manager = model_manager or UnifiedModelManager()
        self.default_model_id = default_model_id or self.config.default_video_model
        
        # Initialize image processor for frame analysis
        self.image_processor = image_processor or ImageProcessor(model_manager)
        
        # Ensure we have a provider prefix
        if self.default_model_id and '/' not in self.default_model_id:
            provider = self.model_manager.get_provider_for_model(self.default_model_id)
            if provider:
                self.default_model_id = f"{provider}/{self.default_model_id}"
    
    def get_default_model_id(self) -> Optional[str]:
        """Get default model ID for this processor."""
        return self.default_model_id
    
    def get_modality(self) -> str:
        """Get modality type of this processor."""
        return "video"
    
    def get_supported_formats(self) -> List[str]:
        """Get supported input formats."""
        return [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"]
    
    def supports_model(self, model_id: str) -> bool:
        """Check if processor supports a specific model."""
        provider = self.model_manager.get_provider_for_model(model_id)
        if not provider:
            return False
        
        # Currently only supports models that can handle images
        return self.image_processor.supports_model(model_id)
    
    def load_video(self, video_path: str) -> Tuple[Optional[cv2.VideoCapture], Dict[str, Any], Optional[str]]:
        """
        Load video from path.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (video_capture, metadata, error_message)
        """
        if not os.path.exists(video_path):
            return None, {}, f"Video file not found: {video_path}"
        
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None, {}, f"Failed to open video: {video_path}"
            
            # Extract video metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            metadata = {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": duration,
                "format": os.path.splitext(video_path)[1][1:].lower(),
                "path": video_path,
                "filename": os.path.basename(video_path)
            }
            
            return cap, metadata, None
            
        except Exception as e:
            logger.error(f"Error loading video: {str(e)}")
            return None, {}, f"Error loading video: {str(e)}"
    
    def extract_frames(
            self, 
            video: Union[str, cv2.VideoCapture],
            max_frames: int = 10,
            sampling_strategy: str = "uniform",
            start_time: Optional[float] = None,
            end_time: Optional[float] = None,
            **kwargs
        ) -> Tuple[List[np.ndarray], Dict[str, Any], Optional[str]]:
        """
        Extract frames from video.
        
        Args:
            video: Video path or OpenCV capture object
            max_frames: Maximum number of frames to extract
            sampling_strategy: How to sample frames ('uniform', 'start', 'end', 'middle')
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
            
        Returns:
            Tuple of (frames, metadata, error_message)
        """
        cap = None
        metadata = {}
        should_release = False
        
        try:
            # Load video if string path provided
            if isinstance(video, str):
                cap, metadata, error = self.load_video(video)
                if error:
                    return [], {}, error
                should_release = True
            else:
                cap = video
                # Get basic metadata
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                metadata = {
                    "fps": fps,
                    "frame_count": frame_count,
                    "width": width,
                    "height": height,
                    "duration": duration
                }
            
            # Determine frame positions to extract
            fps = metadata.get("fps", 30)
            frame_count = int(metadata.get("frame_count", 0))
            
            if frame_count <= 0:
                return [], metadata, "Invalid video: no frames detected"
            
            # Convert time to frame numbers if specified
            start_frame = 0
            if start_time is not None:
                start_frame = int(start_time * fps)
            
            end_frame = frame_count
            if end_time is not None:
                end_frame = min(int(end_time * fps), frame_count)
            
            # Adjust frame count to selection range
            adjusted_frame_count = end_frame - start_frame
            
            # Calculate which frames to extract based on strategy
            frame_indices = []
            if sampling_strategy == "uniform" and adjusted_frame_count > 0:
                if max_frames >= adjusted_frame_count:
                    frame_indices = list(range(start_frame, end_frame))
                else:
                    step = adjusted_frame_count / max_frames
                    frame_indices = [start_frame + int(i * step) for i in range(max_frames)]
            elif sampling_strategy == "start":
                frame_indices = list(range(start_frame, min(start_frame + max_frames, end_frame)))
            elif sampling_strategy == "end":
                frame_indices = list(range(max(end_frame - max_frames, start_frame), end_frame))
            elif sampling_strategy == "middle":
                mid_point = start_frame + adjusted_frame_count // 2
                half_range = min(max_frames // 2, adjusted_frame_count // 2)
                frame_indices = list(range(mid_point - half_range, mid_point + half_range))
            else:
                # Default to uniform if invalid strategy
                step = max(1, adjusted_frame_count // max_frames)
                frame_indices = list(range(start_frame, end_frame, step))[:max_frames]
            
            # Extract the frames
            frames = []
            frame_timestamps = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                    frame_time = frame_idx / fps if fps > 0 else 0
                    frame_timestamps.append(frame_time)
            
            # Update metadata with frame info
            metadata.update({
                "extracted_frames": len(frames),
                "frame_indices": frame_indices,
                "frame_timestamps": frame_timestamps,
                "sampling_strategy": sampling_strategy,
                "max_frames_requested": max_frames
            })
            
            return frames, metadata, None
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return [], metadata, f"Error extracting frames: {str(e)}"
        finally:
            if cap is not None and should_release:
                cap.release()
    
    def validate_input(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if data is a string (file path)
        if isinstance(data, str):
            if not os.path.exists(data):
                return False, f"Video file not found: {data}"
            
            ext = os.path.splitext(data)[1].lower()
            if ext not in self.get_supported_formats():
                return False, f"Unsupported video format: {ext}"
            
            return True, None
            
        # Check if data is a video capture object
        elif isinstance(data, cv2.VideoCapture):
            if not data.isOpened():
                return False, "Video capture is not open"
            return True, None
            
        # Check if data is already a list of frames
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], np.ndarray):
            return True, None
            
        # Check if data is a numpy array (single frame)
        elif isinstance(data, np.ndarray) and len(data.shape) == 3:
            return True, None
            
        return False, "Unsupported video format or type"
    
    def process(
            self, 
            data: Any, 
            model_id: Optional[str] = None,
            return_raw_output: bool = False,
            max_frames: int = 10,
            sampling_strategy: str = "uniform",
            analyze_frames: bool = True,
            summarize: bool = True,
            prompt: Optional[str] = None,
            **kwargs
        ) -> ProcessingResult:
        """
        Process video data using specified model.
        
        Args:
            data: Input video data (path, capture object, or frame list)
            model_id: ID of model to use
            return_raw_output: If True, include raw model output
            max_frames: Maximum number of frames to extract
            sampling_strategy: How to sample frames ('uniform', 'start', 'end', 'middle')
            analyze_frames: Whether to analyze individual frames
            summarize: Whether to generate overall video summary
            prompt: Custom prompt for video analysis
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        start_time = time.time()
        
        # Use default model if none specified
        if not model_id:
            model_id = self.get_default_model_id()
            if not model_id:
                return ProcessingResult(
                    success=False,
                    modality="video",
                    model_id="none",
                    content={},
                    error="No model specified and no default model available",
                    metadata={"processing_time": time.time() - start_time}
                )
        
        # Check if we have enough resources before proceeding
        model_provider = self.model_manager.get_provider_for_model(model_id)
        if not model_provider:
            return ProcessingResult(
                success=False,
                modality="video",
                model_id=model_id,
                content={},
                error=f"Unknown model provider for {model_id}",
                metadata={"processing_time": time.time() - start_time}
            )
        
        # Check resource availability before loading the model
        required_memory = self.config.get_model_memory_requirement(model_id, default=2.0)
        if not self.model_manager.check_resource_availability(required_memory):
            # Try unloading other provider models first
            self.model_manager.unload_all_models(exclude_provider=model_provider)
            
            # Check again if we have enough resources
            if not self.model_manager.check_resource_availability(required_memory):
                # Last resort: unload models from the current provider too
                self.model_manager.unload_all_models(provider=model_provider)
                
                # Final check
                if not self.model_manager.check_resource_availability(required_memory):
                    return ProcessingResult(
                        success=False,
                        modality="video",
                        model_id=model_id,
                        content={},
                        error=f"Insufficient resources to load model {model_id}",
                        metadata={"processing_time": time.time() - start_time}
                    )
        
        # Validate input
        is_valid, error = self.validate_input(data)
        if not is_valid:
            return ProcessingResult(
                success=False,
                modality="video",
                model_id=model_id,
                content={},
                error=error,
                metadata={"processing_time": time.time() - start_time}
            )
        
        # Extract frames from video if needed
        frames = []
        video_metadata = {}
        
        if isinstance(data, str) or isinstance(data, cv2.VideoCapture):
            frames, video_metadata, error = self.extract_frames(
                data, 
                max_frames=max_frames,
                sampling_strategy=sampling_strategy,
                **kwargs
            )
            if error:
                return ProcessingResult(
                    success=False,
                    modality="video",
                    model_id=model_id,
                    content={},
                    error=error,
                    metadata={"processing_time": time.time() - start_time}
                )
            
            if len(frames) == 0:
                return ProcessingResult(
                    success=False,
                    modality="video",
                    model_id=model_id,
                    content={},
                    error="No frames could be extracted from the video",
                    metadata={"processing_time": time.time() - start_time}
                )
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], np.ndarray):
            frames = data
            video_metadata = {"extracted_frames": len(frames)}
        elif isinstance(data, np.ndarray):
            frames = [data]
            video_metadata = {"extracted_frames": 1}
        
        # Process the video data based on provider
        try:
            if model_provider == "ollama":
                return self._process_with_ollama(
                    frames, 
                    model_id,
                    video_metadata=video_metadata,
                    analyze_frames=analyze_frames,
                    summarize=summarize,
                    prompt=prompt,
                    return_raw_output=return_raw_output,
                    **kwargs
                )
            elif model_provider == "huggingface":
                return self._process_with_huggingface(
                    frames, 
                    model_id,
                    video_metadata=video_metadata,
                    analyze_frames=analyze_frames,
                    summarize=summarize,
                    prompt=prompt,
                    return_raw_output=return_raw_output,
                    **kwargs
                )
            else:
                return ProcessingResult(
                    success=False,
                    modality="video",
                    model_id=model_id,
                    content={},
                    error=f"Unsupported model provider: {model_provider}",
                    metadata={"processing_time": time.time() - start_time}
                )
                
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            return ProcessingResult(
                success=False,
                modality="video",
                model_id=model_id,
                content={},
                error=f"Error processing video: {str(e)}",
                metadata={"processing_time": time.time() - start_time}
            )
    
    def _process_with_ollama(
            self, 
            frames: List[np.ndarray],
            model_id: str,
            video_metadata: Dict[str, Any] = None,
            analyze_frames: bool = True,
            summarize: bool = True,
            prompt: Optional[str] = None,
            return_raw_output: bool = False,
            **kwargs
        ) -> ProcessingResult:
        """
        Process video with Ollama model.
        
        Args:
            frames: List of video frames as numpy arrays
            model_id: Full model ID including provider
            video_metadata: Metadata about the video
            analyze_frames: Whether to analyze individual frames
            summarize: Whether to generate overall video summary
            prompt: Custom prompt to use with frames
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        start_time = time.time()
        frame_results = []
        raw_outputs = []
        
        # Configure default prompt if not provided
        if not prompt:
            if summarize and not analyze_frames:
                prompt = "Analyze this sequence of video frames and provide a detailed summary of the video content."
            elif analyze_frames and not summarize:
                prompt = "Describe what you see in this video frame in detail."
            else:
                prompt = "Describe this video frame and its context within the video sequence."
        
        # Process individual frames if requested
        if analyze_frames:
            for i, frame in enumerate(frames):
                # Create a frame-specific prompt if analyzing multiple frames
                frame_prompt = prompt
                if len(frames) > 1 and summarize:
                    frame_num = i + 1
                    frame_prompt = f"Frame {frame_num}/{len(frames)}: {prompt}"
                
                # Process the frame using the image processor
                result = self.image_processor.process(
                    frame,
                    model_id=model_id,
                    prompt=frame_prompt,
                    return_raw_output=True,
                    **kwargs
                )
                
                if result.success:
                    # Add frame number to result metadata
                    frame_metadata = result.metadata.copy() if result.metadata else {}
                    frame_metadata.update({"frame_index": i})
                    
                    # Add timestamp if available
                    if video_metadata and "frame_timestamps" in video_metadata and i < len(video_metadata["frame_timestamps"]):
                        frame_metadata["timestamp"] = video_metadata["frame_timestamps"][i]
                    
                    frame_result = {
                        "frame_index": i,
                        "analysis": result.content,
                        "metadata": frame_metadata
                    }
                    
                    frame_results.append(frame_result)
                    if return_raw_output and result.raw_output:
                        raw_outputs.append(result.raw_output)
                else:
                    logger.warning(f"Failed to analyze frame {i}: {result.error}")
        
        # Generate video summary if requested
        summary = None
        summary_raw_output = None
        
        if summarize and len(frames) > 1:
            # For video summary, we'll use a sample of frames
            sample_frames = []
            sample_indices = []
            
            # Select representative frames for summary
            if len(frames) <= 5:
                sample_frames = frames
                sample_indices = list(range(len(frames)))
            else:
                # Sample frames evenly across the video
                step = len(frames) / min(5, len(frames))
                for i in range(min(5, len(frames))):
                    idx = min(int(i * step), len(frames) - 1)
                    sample_frames.append(frames[idx])
                    sample_indices.append(idx)
            
            # Create a temporary directory for the frames
            with tempfile.TemporaryDirectory() as temp_dir:
                frame_paths = []
                
                # Save frames as images
                for i, frame in enumerate(sample_frames):
                    frame_path = os.path.join(temp_dir, f"frame_{i}.jpg")
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                
                # Create a prompt for the video summary
                summary_prompt = (
                    f"Analyze these {len(sample_frames)} frames from a video and provide a comprehensive summary. "
                    "Describe what's happening in the video, key elements, any changes or movements, "
                    "and the overall context or story."
                )
                
                if prompt and "summary" in prompt.lower():
                    summary_prompt = prompt
                
                # Use the model to analyze the collection of frames
                try:
                    # For Ollama, we'll use the first frame with a special prompt
                    # (Most Ollama models can't handle multiple images yet)
                    result = self.model_manager.generate_with_images(
                        provider="ollama",
                        model_name=model_id.split("/")[1] if "/" in model_id else model_id,
                        prompt=summary_prompt,
                        image_paths=[frame_paths[0]],  # Just use the first frame for now
                        **kwargs
                    )
                    
                    if result and "response" in result:
                        summary = result["response"]
                        summary_raw_output = result
                    else:
                        logger.warning("Failed to generate video summary: empty response")
                        
                except Exception as e:
                    logger.error(f"Error generating video summary: {str(e)}")
        
        # Prepare the final result
        processing_time = time.time() - start_time
        
        # Combine metadata
        metadata = video_metadata or {}
        metadata.update({
            "processing_time": processing_time,
            "model_id": model_id,
            "provider": "ollama",
            "frames_analyzed": len(frame_results) if analyze_frames else 0,
            "frames_extracted": len(frames)
        })
        
        # Prepare the result dictionary
        result_dict = {}
        if frame_results:
            result_dict["frame_analyses"] = frame_results
        
        if summary:
            result_dict["summary"] = summary
        
        # Include raw output if requested
        raw_output = None
        if return_raw_output:
            raw_output = {
                "frame_outputs": raw_outputs if raw_outputs else None,
                "summary_output": summary_raw_output
            }
        
        return ProcessingResult(
            success=True,
            modality="video",
            model_id=model_id,
            content=result_dict,
            metadata=metadata
        )
    
    def _process_with_huggingface(
            self, 
            frames: List[np.ndarray],
            model_id: str,
            video_metadata: Dict[str, Any] = None,
            analyze_frames: bool = True,
            summarize: bool = True,
            prompt: Optional[str] = None,
            return_raw_output: bool = False,
            **kwargs
        ) -> ProcessingResult:
        """
        Process video with Hugging Face model.
        
        Args:
            frames: List of video frames as numpy arrays
            model_id: Full model ID including provider
            video_metadata: Metadata about the video
            analyze_frames: Whether to analyze individual frames
            summarize: Whether to generate overall video summary
            prompt: Custom prompt to use with frames
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        start_time = time.time()
        
        # Check if HuggingFace is available
        if not self.model_manager.is_provider_available("huggingface"):
            return ProcessingResult(
                success=False,
                modality="video",
                model_id=model_id,
                content={},
                error="HuggingFace provider is not available",
                metadata={"processing_time": time.time() - start_time}
            )
        
        # The implementation would be similar to Ollama but using HuggingFace APIs
        # For now, we'll return a placeholder since this would require the proper HF setup
        
        # This would be replaced with actual HuggingFace implementation
        return ProcessingResult(
            success=False,
            modality="video",
            model_id=model_id,
            content={},
            error="HuggingFace video processing not yet implemented",
            metadata={"processing_time": time.time() - start_time, "frames_count": len(frames)}
        )
