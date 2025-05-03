#!/usr/bin/env python3
"""
Multimodal Processor

Implements the BaseProcessor interface for combined modality processing.
Handles inputs that combine multiple modalities (e.g., text + image).
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import json
from pathlib import Path

from multimodal.processors.base_processor import BaseProcessor, ProcessingResult
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.processors.image_processor import ImageProcessor
from multimodal.processors.text_processor import TextProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Supported multimodal formats
SUPPORTED_MULTIMODAL_FORMATS = [
    # Multimodal format identifiers
    "text+image", "image+text", "text+video", "video+text"
]


class MultimodalProcessor(BaseProcessor):
    """
    Processor for multimodal data.
    
    This processor handles combined modality inputs, such as text+image,
    coordinating between specialized processors for optimal results.
    """
    
    def __init__(
        self, 
        model_manager: Optional[UnifiedModelManager] = None,
        default_model_id: Optional[str] = None
    ):
        """
        Initialize multimodal processor.
        
        Args:
            model_manager: Model manager for accessing models
            default_model_id: Default model ID to use
        """
        from multimodal.utils.config import get_config
        self.config = get_config()
        self.model_manager = model_manager or UnifiedModelManager()
        self.default_model_id = default_model_id or self.config.default_multimodal_model
        
        # If no explicit multimodal model is set, use the image model as default
        if not self.default_model_id:
            self.default_model_id = self.config.default_image_model
        
        # Ensure we have a provider prefix
        if self.default_model_id and '/' not in self.default_model_id:
            provider = self.model_manager.get_provider_for_model(self.default_model_id)
            if provider:
                self.default_model_id = f"{provider}/{self.default_model_id}"
        
        # Initialize specialized processors
        self.image_processor = ImageProcessor(model_manager)
        self.text_processor = TextProcessor(model_manager)
    
    def get_default_model_id(self) -> str:
        """Get default model ID for this processor."""
        return self.default_model_id
    
    def get_modality(self) -> str:
        """Get modality type of this processor."""
        return "multimodal"
    
    def get_supported_formats(self) -> List[str]:
        """Get supported input formats."""
        return SUPPORTED_MULTIMODAL_FORMATS
    
    def supports_model(self, model_id: str) -> bool:
        """Check if processor supports a specific model."""
        # Extract model info
        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            return False
        
        # Check if model has both image and text capabilities
        return "image" in model_info.capabilities and "text" in model_info.capabilities
    
    def validate_input(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if input is a dictionary with required keys
        if not isinstance(data, dict):
            return False, f"Expected dictionary input, got {type(data)}"
        
        # Check for required modalities
        has_text = "text" in data and data["text"]
        has_image = "image" in data and data["image"]
        has_video = "video" in data and data["video"]
        
        # Must have text and either image or video
        if not has_text:
            return False, "Missing 'text' key in multimodal input"
        
        if not (has_image or has_video):
            return False, "Missing 'image' or 'video' key in multimodal input"
        
        # Validate individual components
        if has_image:
            is_valid, error = self.image_processor.validate_input(data["image"])
            if not is_valid:
                return False, f"Invalid image input: {error}"
        
        if has_video:
            # Would use video_processor here if implemented
            pass
        
        if has_text:
            is_valid, error = self.text_processor.validate_input(data["text"])
            if not is_valid:
                return False, f"Invalid text input: {error}"
        
        return True, None
    
    def process(
        self, 
        data: Any, 
        model_id: Optional[str] = None,
        return_raw_output: bool = False,
        **kwargs
    ) -> ProcessingResult:
        """
        Process multimodal data using specified model.
        
        Args:
            data: Input multimodal data (dictionary with modality keys)
            model_id: ID of model to use
            return_raw_output: If True, include raw model output
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        # Start timing
        start_time = time.time()
        
        # Validate input
        is_valid, error = self.validate_input(data)
        if not is_valid:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=model_id or self.default_model_id,
                error_message=error
            )
        
        # Determine model to use
        actual_model_id = model_id or self.default_model_id
        
        # Check if model supports multimodal
        model_info = self.model_manager.get_model_info(actual_model_id)
        if not model_info:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=actual_model_id,
                error_message=f"Model {actual_model_id} not found"
            )
        
        # Ensure model is multimodal
        if "image" not in model_info.capabilities or "text" not in model_info.capabilities:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=actual_model_id,
                error_message=f"Model {actual_model_id} does not support multimodal processing"
            )
        
        # Ensure model is available
        if not self.model_manager.is_model_available(actual_model_id):
            try:
                logger.info(f"Model {actual_model_id} not available locally, attempting to download")
                success = self.model_manager.ensure_model_availability(actual_model_id)
                if not success:
                    return ProcessingResult.error_result(
                        modality="multimodal",
                        model_id=actual_model_id,
                        error_message=f"Model {actual_model_id} not available and could not be downloaded"
                    )
            except Exception as e:
                return ProcessingResult.error_result(
                    modality="multimodal",
                    model_id=actual_model_id,
                    error_message=f"Error ensuring model availability: {str(e)}"
                )
        
        # Check resource availability
        provider, model_name = self.model_manager._parse_model_id(actual_model_id)
        model_info = self.model_manager.get_model_info(actual_model_id)
        
        # Multimodal models typically require more memory
        required_memory_gb = 4.0  # Higher default for multimodal
        if model_info and hasattr(model_info, 'min_ram_gb'):
            required_memory_gb = model_info.min_ram_gb
        
        # Check if resources are available
        if not self.model_manager.check_resource_availability(required_memory_gb):
            logger.warning(f"Insufficient memory for model {actual_model_id}, attempting to free resources")
            
            # Unload ALL models to maximize available memory for multimodal processing
            self.model_manager.unload_all_models()
            
            # Final check
            if not self.model_manager.check_resource_availability(required_memory_gb):
                return ProcessingResult.error_result(
                    modality="multimodal",
                    model_id=actual_model_id,
                    error_message=f"Insufficient memory to load model {actual_model_id}, even after unloading all models"
                )
        
        # After this point, we should have enough resources to load the model
        
        # Extract data
        text_data = data.get("text", "")
        image_data = data.get("image")
        video_data = data.get("video")
        prompt = kwargs.get("prompt", text_data)
        
        # Determine processing type
        if image_data:
            primary_media = "image"
            media_data = image_data
        elif video_data:
            primary_media = "video"
            media_data = video_data
        else:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=actual_model_id,
                error_message="No media data found in input"
            )
        
        # Parse model_id to get provider and name
        provider = self.model_manager.get_provider_for_model(actual_model_id)
        if not provider:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=actual_model_id,
                error_message=f"Could not determine provider for model {actual_model_id}"
            )
        
        # Process based on provider
        try:
            if provider == "ollama":
                result = self._process_with_ollama(
                    text_data, media_data, primary_media, actual_model_id, **kwargs
                )
            elif provider == "huggingface":
                result = self._process_with_huggingface(
                    text_data, media_data, primary_media, actual_model_id, **kwargs
                )
            else:
                return ProcessingResult.error_result(
                    modality="multimodal",
                    model_id=actual_model_id,
                    error_message=f"Unsupported provider: {provider}"
                )
            
            # Add metadata
            processing_time = time.time() - start_time
            result.metadata["processing_time"] = processing_time
            result.metadata["timestamp"] = datetime.now().isoformat()
            result.metadata["modalities"] = [primary_media, "text"]
            
            # Remove raw output if not requested
            if not return_raw_output and "raw_output" in result.content:
                del result.content["raw_output"]
            
            return result
        except Exception as e:
            error_msg = f"Error processing multimodal input: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=actual_model_id,
                error_message=error_msg
            )
    
    def _process_with_ollama(
        self, 
        text_data: str,
        media_data: Any,
        media_type: str,
        model_id: str,
        **kwargs
    ) -> ProcessingResult:
        """
        Process multimodal data with Ollama model.
        
        Args:
            text_data: Text content to process
            media_data: Media data (image or video)
            media_type: Type of media ('image' or 'video')
            model_id: Full model ID including provider
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            # For Ollama, we can delegate to the image processor
            # since its _process_with_ollama already handles text+image
            if media_type == "image":
                # We need to prepare combined input for the image processor
                # using the provided text as prompt
                image_result = self.image_processor._process_with_ollama(
                    media_data, model_id, prompt=text_data, **kwargs
                )
                
                # Adjust modality and content
                if image_result.success:
                    return ProcessingResult(
                        success=True,
                        modality="multimodal",
                        model_id=model_id,
                        content=image_result.content,
                        metadata=image_result.metadata
                    )
                else:
                    return ProcessingResult.error_result(
                        modality="multimodal",
                        model_id=model_id,
                        error_message=image_result.error
                    )
            else:
                return ProcessingResult.error_result(
                    modality="multimodal",
                    model_id=model_id,
                    error_message=f"Ollama multimodal processing for {media_type} not yet implemented"
                )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=model_id,
                error_message=f"Error processing with Ollama: {str(e)}"
            )
    
    def _process_with_huggingface(
        self, 
        text_data: str,
        media_data: Any,
        media_type: str,
        model_id: str,
        **kwargs
    ) -> ProcessingResult:
        """
        Process multimodal data with Hugging Face model.
        
        Args:
            text_data: Text content to process
            media_data: Media data (image or video)
            media_type: Type of media ('image' or 'video')
            model_id: Full model ID including provider
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            # For Hugging Face, we can delegate to the image processor
            # since its _process_with_huggingface already handles text+image
            if media_type == "image":
                # Use provided text as prompt
                image_result = self.image_processor._process_with_huggingface(
                    media_data, model_id, prompt=text_data, **kwargs
                )
                
                # Adjust modality
                if image_result.success:
                    return ProcessingResult(
                        success=True,
                        modality="multimodal",
                        model_id=model_id,
                        content=image_result.content,
                        metadata=image_result.metadata
                    )
                else:
                    return ProcessingResult.error_result(
                        modality="multimodal",
                        model_id=model_id,
                        error_message=image_result.error
                    )
            else:
                return ProcessingResult.error_result(
                    modality="multimodal",
                    model_id=model_id,
                    error_message=f"Hugging Face multimodal processing for {media_type} not yet implemented"
                )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="multimodal",
                model_id=model_id,
                error_message=f"Error processing with Hugging Face: {str(e)}"
            )
