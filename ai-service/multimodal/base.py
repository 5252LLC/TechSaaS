#!/usr/bin/env python3
"""
Multimodal Processing Base Module

This is the main entry point for the multimodal processing system, providing:
1. Hardware capability detection and adaptation
2. Model selection and management
3. Configuration handling
4. Core interfaces for the multimodal processing pipeline

Usage:
    from multimodal.base import MultimodalSystem
    
    # Initialize with hardware detection and configuration
    mm_system = MultimodalSystem()
    
    # Process an image with automatic model selection
    result = mm_system.process_image("path/to/image.jpg")
    
    # Process a video
    video_result = mm_system.process_video("path/to/video.mp4")
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

# Import utility modules
from multimodal.utils.hardware import get_current_hardware_profile, HardwareProfile
from multimodal.utils.config import get_config, MultimodalConfig, ModelConfig

# Configure logging
logger = logging.getLogger(__name__)


class MultimodalSystem:
    """
    Main class for multimodal processing system.
    
    This class coordinates hardware detection, configuration, and processing
    to provide a simplified interface for multimodal tasks.
    """
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        hardware_detection: bool = True,
        force_cpu: bool = False
    ):
        """
        Initialize the multimodal processing system.
        
        Args:
            config_path: Path to configuration file (optional)
            hardware_detection: Whether to detect hardware capabilities
            force_cpu: Force CPU-only operation regardless of hardware
        """
        # Set up logging
        self._setup_logging()
        
        # Load configuration
        logger.info("Initializing multimodal processing system")
        self.config = get_config() if config_path is None else get_config(reload=True)
        
        # Detect hardware capabilities
        if hardware_detection:
            self.hardware = get_current_hardware_profile()
            logger.info(f"Hardware capability level: {self.hardware.get_capability_level()}")
            
            # Adapt configuration to hardware if enabled
            if self.config.adapt_to_hardware:
                self._adapt_to_hardware()
        else:
            logger.info("Hardware detection disabled")
            self.hardware = None
        
        # Force CPU if requested
        if force_cpu:
            logger.info("Forcing CPU-only operation")
            self.config.gpu_preferred = False
            
        # Initialize model providers (lazy-loaded when needed)
        self._ollama_models = None
        self._huggingface_models = None
        
        # Set up processing components (lazy-loaded when needed)
        self._image_processor = None
        self._video_processor = None
        self._text_processor = None
        
        logger.info("Multimodal system initialized and ready")
    
    def _setup_logging(self):
        """Set up logging for the multimodal system."""
        # This will be handled by the application-wide logging configuration
        pass
    
    def _adapt_to_hardware(self):
        """Adapt configuration based on detected hardware capabilities."""
        if not self.hardware:
            logger.warning("Cannot adapt to hardware: no hardware profile available")
            return
        
        logger.info("Adapting configuration to hardware capabilities")
        capability = self.hardware.get_capability_level()
        
        # Adjust batch size based on capability
        if capability == "low":
            self.config.processing.batch_size = 2
            self.config.processing.max_frames = 15
            self.config.processing.image_size = 384
        elif capability == "medium":
            self.config.processing.batch_size = 4
            self.config.processing.max_frames = 30
            self.config.processing.image_size = 512
        elif capability == "high":
            self.config.processing.batch_size = 8
            self.config.processing.max_frames = 60
            self.config.processing.image_size = 768
        
        # Adjust GPU preference based on availability
        self.config.gpu_preferred = self.hardware.has_gpu
        
        # Select appropriate default models based on hardware
        self._adjust_default_models()
        
        logger.info(f"Configuration adapted to {capability} hardware capability")
    
    def _adjust_default_models(self):
        """Select appropriate default models based on hardware capability."""
        if not self.hardware:
            return
        
        # Check if default models can run on the hardware
        for model_type, model_name in [
            ("image", self.config.default_image_model),
            ("video", self.config.default_video_model),
            ("text", self.config.default_text_model)
        ]:
            if model_name in self.config.models:
                model_config = self.config.models[model_name]
                if not self._can_run_model(model_config):
                    # Use fallback if available
                    if model_config.fallback_model and model_config.fallback_model in self.config.models:
                        fallback = model_config.fallback_model
                        logger.info(f"Using fallback model for {model_type}: {fallback}")
                        if model_type == "image":
                            self.config.default_image_model = fallback
                        elif model_type == "video":
                            self.config.default_video_model = fallback
                        elif model_type == "text":
                            self.config.default_text_model = fallback
                    else:
                        logger.warning(f"No suitable fallback for {model_name} on current hardware")
    
    def _can_run_model(self, model_config: ModelConfig) -> bool:
        """Check if a model can run on the current hardware."""
        if not self.hardware:
            return True  # Assume it can run if hardware detection is disabled
        
        # Convert model config to requirements dict
        requirements = {
            "min_ram_gb": model_config.min_ram_gb,
            "min_gpu_gb": model_config.min_gpu_gb,
            "requires_gpu": model_config.requires_gpu
        }
        
        return self.hardware.can_run_model(requirements)
    
    def _get_suitable_models(self, task_type: str) -> List[str]:
        """
        Get list of suitable models for a specific task based on hardware.
        
        Args:
            task_type: Type of task ("image", "video", "text")
            
        Returns:
            List of model names suitable for the task
        """
        suitable_models = []
        
        for name, model_config in self.config.models.items():
            # Check if model is suitable for the task
            if task_type in model_config.tags:
                # Check if model can run on the hardware
                if self._can_run_model(model_config):
                    suitable_models.append(name)
        
        return suitable_models
    
    def get_default_model(self, task_type: str) -> str:
        """
        Get the default model for a specific task.
        
        Args:
            task_type: Type of task ("image", "video", "text")
            
        Returns:
            Name of default model for the task
        """
        if task_type == "image":
            return self.config.default_image_model
        elif task_type == "video":
            return self.config.default_video_model
        elif task_type == "text":
            return self.config.default_text_model
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Get information about the current hardware.
        
        Returns:
            Dict with hardware information
        """
        if not self.hardware:
            return {"detected": False, "capability": "unknown"}
        
        return {
            "detected": True,
            "capability": self.hardware.get_capability_level(),
            "has_gpu": self.hardware.has_gpu,
            "gpus": [{"name": gpu.name, "memory_gb": gpu.memory_gb} for gpu in self.hardware.gpus],
            "ram_gb": {
                "total": self.hardware.total_ram_gb,
                "available": self.hardware.available_ram_gb
            },
            "cpu_count": self.hardware.cpu_count,
            "platform": self.hardware.platform
        }
    
    def get_suitable_image_models(self) -> List[str]:
        """Get list of suitable image models."""
        return self._get_suitable_models("image")
    
    def get_suitable_video_models(self) -> List[str]:
        """Get list of suitable video models."""
        return self._get_suitable_models("video")
    
    def get_suitable_text_models(self) -> List[str]:
        """Get list of suitable text models."""
        return self._get_suitable_models("text")
    
    # These methods will be implemented when we develop the processors in Task 11.3
    def process_image(self, image_path: str, model_name: Optional[str] = None):
        """
        Process an image using a specified model or the default.
        
        Args:
            image_path: Path to the image file
            model_name: Name of the model to use (optional)
            
        Returns:
            Processing result (implementation TBD)
        """
        logger.info(f"Image processing requested: {image_path}")
        model = model_name or self.config.default_image_model
        logger.info(f"Using model: {model}")
        
        # This will be implemented in Task 11.3
        return {"status": "pending_implementation", "model": model, "image": image_path}
    
    def process_video(self, video_path: str, model_name: Optional[str] = None):
        """
        Process a video using a specified model or the default.
        
        Args:
            video_path: Path to the video file
            model_name: Name of the model to use (optional)
            
        Returns:
            Processing result (implementation TBD)
        """
        logger.info(f"Video processing requested: {video_path}")
        model = model_name or self.config.default_video_model
        logger.info(f"Using model: {model}")
        
        # This will be implemented in Task 11.3
        return {"status": "pending_implementation", "model": model, "video": video_path}
    
    def process_text(self, text: str, model_name: Optional[str] = None):
        """
        Process text using a specified model or the default.
        
        Args:
            text: Text to process
            model_name: Name of the model to use (optional)
            
        Returns:
            Processing result (implementation TBD)
        """
        logger.info(f"Text processing requested: {text[:50]}...")
        model = model_name or self.config.default_text_model
        logger.info(f"Using model: {model}")
        
        # This will be implemented in Task 11.3
        return {"status": "pending_implementation", "model": model, "text": text[:50] + "..."}
    
    def process_multimodal(self, text: str, media_path: str, model_name: Optional[str] = None):
        """
        Process text and media together using a specified model or the default.
        
        Args:
            text: Text to process
            media_path: Path to the media file (image or video)
            model_name: Name of the model to use (optional)
            
        Returns:
            Processing result (implementation TBD)
        """
        logger.info(f"Multimodal processing requested: {media_path} with text {text[:50]}...")
        
        # Determine media type based on file extension
        if media_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
            model = model_name or self.config.default_image_model
            media_type = "image"
        elif media_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            model = model_name or self.config.default_video_model
            media_type = "video"
        else:
            raise ValueError(f"Unsupported media type: {media_path}")
        
        logger.info(f"Using model: {model} for {media_type}")
        
        # This will be implemented in Task 11.3
        return {
            "status": "pending_implementation", 
            "model": model, 
            "media_type": media_type,
            "media_path": media_path,
            "text": text[:50] + "..."
        }


if __name__ == "__main__":
    # Set up logging for command-line usage
    logging.basicConfig(level=logging.INFO)
    
    # Initialize multimodal system
    system = MultimodalSystem()
    
    # Print hardware info
    print("\nHardware Information:")
    print("====================")
    hw_info = system.get_hardware_info()
    for key, value in hw_info.items():
        print(f"{key}: {value}")
    
    # Print suitable models
    print("\nSuitable Image Models:", system.get_suitable_image_models())
    print("Suitable Video Models:", system.get_suitable_video_models())
    print("Suitable Text Models:", system.get_suitable_text_models())
    
    # Print default models
    print("\nDefault Models:")
    print("==============")
    print(f"Image: {system.get_default_model('image')}")
    print(f"Video: {system.get_default_model('video')}")
    print(f"Text: {system.get_default_model('text')}")
