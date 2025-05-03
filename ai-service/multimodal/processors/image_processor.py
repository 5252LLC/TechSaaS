#!/usr/bin/env python3
"""
Image Processor

Implements the BaseProcessor interface for image processing.
Handles loading, preprocessing, and analysis of images using various models.
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
import json
from pathlib import Path

# Import optional image processing libraries with graceful fallback
try:
    import numpy as np
    from PIL import Image, UnidentifiedImageError
    import cv2
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Image processing libraries not installed, functionality will be limited")

from multimodal.processors.base_processor import BaseProcessor, ProcessingResult
from multimodal.models.unified_manager import UnifiedModelManager

# Configure logging
logger = logging.getLogger(__name__)

# Supported image formats
SUPPORTED_IMAGE_FORMATS = [
    # Common file extensions
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif',
    
    # MIME types
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 
    'image/webp', 'image/tiff'
]


class ImageProcessor(BaseProcessor):
    """
    Processor for image data.
    
    This processor handles the loading, preprocessing, and analysis of images
    using various models from different providers.
    """
    
    def __init__(
        self, 
        model_manager: Optional[UnifiedModelManager] = None,
        default_model_id: Optional[str] = None
    ):
        """
        Initialize image processor.
        
        Args:
            model_manager: Model manager for accessing models
            default_model_id: Default model ID to use
        """
        if not IMAGE_PROCESSING_AVAILABLE:
            logger.error("Image processing libraries not installed")
            raise ImportError(
                "Image processing libraries are required. "
                "Install with pip install pillow opencv-python"
            )
        
        from multimodal.utils.config import get_config
        self.config = get_config()
        self.model_manager = model_manager or UnifiedModelManager()
        self.default_model_id = default_model_id or self.config.default_image_model
        
        # Ensure we have a provider prefix
        if self.default_model_id and '/' not in self.default_model_id:
            provider = self.model_manager.get_provider_for_model(self.default_model_id)
            if provider:
                self.default_model_id = f"{provider}/{self.default_model_id}"
    
    def get_default_model_id(self) -> str:
        """Get default model ID for this processor."""
        return self.default_model_id
    
    def get_modality(self) -> str:
        """Get modality type of this processor."""
        return "image"
    
    def get_supported_formats(self) -> List[str]:
        """Get supported input formats."""
        return SUPPORTED_IMAGE_FORMATS
    
    def supports_model(self, model_id: str) -> bool:
        """Check if processor supports a specific model."""
        # Extract model info
        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            return False
        
        # Check if model has image capability
        return "image" in model_info.capabilities
    
    def load_image(self, image_path: str) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        Load image from path.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple of (image_array, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                return None, f"Image file not found: {image_path}"
            
            # Try loading with PIL first (handles more formats)
            try:
                with Image.open(image_path) as img:
                    img = img.convert('RGB')  # Convert to RGB
                    return np.array(img), None
            except UnidentifiedImageError:
                # Fall back to OpenCV
                img = cv2.imread(image_path)
                if img is None:
                    return None, f"Failed to load image: {image_path}"
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
                return img, None
        except Exception as e:
            return None, f"Error loading image: {str(e)}"
    
    def preprocess_image(
        self, 
        image: Union[str, np.ndarray, Image.Image],
        target_size: Optional[Tuple[int, int]] = None,
        **kwargs
    ) -> Tuple[Optional[np.ndarray], Optional[Dict[str, Any]], Optional[str]]:
        """
        Preprocess image for model input.
        
        Args:
            image: Image as path, array, or PIL Image
            target_size: Target size as (width, height)
            **kwargs: Additional preprocessing options
            
        Returns:
            Tuple of (processed_image, metadata, error_message)
        """
        try:
            # If image is a string, load it
            if isinstance(image, str):
                img_array, error = self.load_image(image)
                if error:
                    return None, None, error
                image = img_array
            
            # If image is a PIL Image, convert to array
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Ensure image is in RGB format
            if image.shape[2] == 4:  # RGBA
                # Create new RGB image with white background
                rgb_image = np.ones((image.shape[0], image.shape[1], 3), dtype=np.uint8) * 255
                alpha = image[:, :, 3:4] / 255.0
                rgb_image = (rgb_image * (1 - alpha) + image[:, :, :3] * alpha).astype(np.uint8)
                image = rgb_image
            elif image.shape[2] == 1:  # Grayscale
                image = np.repeat(image, 3, axis=2)
            
            # Resize if target size specified
            orig_size = image.shape[:2]  # (height, width)
            metadata = {"original_size": orig_size}
            
            if target_size:
                target_h, target_w = target_size
                image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
                metadata["resized"] = True
                metadata["target_size"] = target_size
            
            # Normalize pixel values to [0, 1]
            image_norm = image.astype(np.float32) / 255.0
            metadata["normalization"] = "0-1"
            
            return image_norm, metadata, None
        except Exception as e:
            return None, None, f"Error preprocessing image: {str(e)}"
    
    def validate_input(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if input is a string (path)
        if isinstance(data, str):
            if not os.path.exists(data):
                return False, f"Image file not found: {data}"
            
            # Check if file is an image
            _, ext = os.path.splitext(data.lower())
            if ext not in SUPPORTED_IMAGE_FORMATS:
                # Try to load it anyway, but warn
                logger.warning(f"Unrecognized image extension: {ext}")
        
        # Check if input is a numpy array or PIL Image
        elif isinstance(data, np.ndarray):
            if len(data.shape) < 2 or len(data.shape) > 3:
                return False, "Invalid image shape: must be 2D or 3D array"
        elif isinstance(data, Image.Image):
            # PIL Image is valid
            pass
        else:
            return False, f"Unsupported input type: {type(data)}"
        
        return True, None
    
    def process(
        self, 
        data: Any, 
        model_id: Optional[str] = None,
        return_raw_output: bool = False,
        **kwargs
    ) -> ProcessingResult:
        """
        Process image data using specified model.
        
        Args:
            data: Input image data (path, array, or PIL Image)
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
                modality="image",
                model_id=model_id or self.default_model_id,
                error_message=error
            )
        
        # Determine model to use
        actual_model_id = model_id or self.default_model_id
        
        # Ensure model is available
        if not self.model_manager.is_model_available(actual_model_id):
            try:
                logger.info(f"Model {actual_model_id} not available locally, attempting to download")
                success = self.model_manager.ensure_model_availability(actual_model_id)
                if not success:
                    return ProcessingResult.error_result(
                        modality="image",
                        model_id=actual_model_id,
                        error_message=f"Model {actual_model_id} not available and could not be downloaded"
                    )
            except Exception as e:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=actual_model_id,
                    error_message=f"Error ensuring model availability: {str(e)}"
                )
        
        # Check resource availability
        provider, model_name = self.model_manager._parse_model_id(actual_model_id)
        model_info = self.model_manager.get_model_info(actual_model_id)
        
        # Estimate memory requirements - either from model info or use default values
        required_memory_gb = 2.0  # Default minimum
        if model_info and hasattr(model_info, 'min_ram_gb'):
            required_memory_gb = model_info.min_ram_gb
        
        # Check if resources are available
        if not self.model_manager.check_resource_availability(required_memory_gb):
            logger.warning(f"Insufficient memory for model {actual_model_id}, attempting to free resources")
            
            # Unload other models to free up resources
            # First, unload models from other providers
            other_providers = [p for p in self.model_manager.list_active_providers() if p != provider]
            for other_provider in other_providers:
                self.model_manager.unload_all_models(other_provider)
            
            # If still not enough resources, unload models from same provider
            if not self.model_manager.check_resource_availability(required_memory_gb):
                self.model_manager.unload_all_models(provider)
                
                # Final check
                if not self.model_manager.check_resource_availability(required_memory_gb):
                    return ProcessingResult.error_result(
                        modality="image",
                        model_id=actual_model_id,
                        error_message=f"Insufficient memory to load model {actual_model_id}, even after unloading other models"
                    )
        
        # Prepare input
        try:
            # Process input based on model capabilities
            image_data = data
            
            # For string inputs (paths), load the image
            if isinstance(data, str):
                image_array, error = self.load_image(data)
                if error:
                    return ProcessingResult.error_result(
                        modality="image",
                        model_id=actual_model_id,
                        error_message=error
                    )
                image_data = image_array
            
            # Parse model_id to get provider and name
            provider = self.model_manager.get_provider_for_model(actual_model_id)
            if not provider:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=actual_model_id,
                    error_message=f"Could not determine provider for model {actual_model_id}"
                )
            
            # Process based on provider
            if provider == "ollama":
                result = self._process_with_ollama(image_data, actual_model_id, **kwargs)
            elif provider == "huggingface":
                result = self._process_with_huggingface(image_data, actual_model_id, **kwargs)
            else:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=actual_model_id,
                    error_message=f"Unsupported provider: {provider}"
                )
            
            # Add metadata
            processing_time = time.time() - start_time
            result.metadata["processing_time"] = processing_time
            result.metadata["timestamp"] = datetime.now().isoformat()
            
            # Remove raw output if not requested
            if not return_raw_output and "raw_output" in result.content:
                del result.content["raw_output"]
            
            return result
        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ProcessingResult.error_result(
                modality="image",
                model_id=actual_model_id,
                error_message=error_msg
            )
    
    def _process_with_ollama(
        self, 
        image_data: Union[np.ndarray, Image.Image],
        model_id: str,
        prompt: str = "Describe this image in detail.",
        **kwargs
    ) -> ProcessingResult:
        """
        Process image with Ollama model.
        
        Args:
            image_data: Image data as array or PIL Image
            model_id: Full model ID including provider
            prompt: Text prompt to use with image
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            import base64
            import io
            import httpx
            
            # Get Ollama manager
            ollama_manager = self.model_manager.get_manager_for_provider("ollama")
            if not ollama_manager:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=model_id,
                    error_message="Ollama manager not available"
                )
            
            # Extract model name from model_id
            _, model_name = self.model_manager._parse_model_id(model_id)
            
            # Convert image to base64
            if isinstance(image_data, np.ndarray):
                # Convert numpy array to PIL Image
                image = Image.fromarray(image_data.astype('uint8'))
            else:
                image = image_data
            
            # Convert to JPEG format in buffer
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Prepare request
            endpoint = f"{ollama_manager.ollama_host}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "images": [img_str],
                "stream": False,
                "options": kwargs.get("options", {})
            }
            
            # Make request
            response = httpx.post(endpoint, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            
            # Extract response
            model_output = result.get("response", "")
            
            # Create result
            return ProcessingResult(
                success=True,
                modality="image",
                model_id=model_id,
                content={
                    "description": model_output,
                    "prompt": prompt,
                    "raw_output": result
                }
            )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="image",
                model_id=model_id,
                error_message=f"Error processing with Ollama: {str(e)}"
            )
    
    def _process_with_huggingface(
        self, 
        image_data: Union[np.ndarray, Image.Image],
        model_id: str,
        prompt: str = "Describe this image in detail.",
        **kwargs
    ) -> ProcessingResult:
        """
        Process image with Hugging Face model.
        
        Args:
            image_data: Image data as array or PIL Image
            model_id: Full model ID including provider
            prompt: Text prompt to use with image
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            # Get Hugging Face manager
            hf_manager = self.model_manager.get_manager_for_provider("huggingface")
            if not hf_manager:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=model_id,
                    error_message="Hugging Face manager not available"
                )
            
            # Extract model name from model_id
            _, model_name = self.model_manager._parse_model_id(model_id)
            
            # Ensure model is loaded
            if not hf_manager.is_model_loaded(model_name):
                logger.info(f"Loading model {model_name}")
                success = hf_manager.load_model(model_name)
                if not success:
                    return ProcessingResult.error_result(
                        modality="image",
                        model_id=model_id,
                        error_message=f"Failed to load model {model_name}"
                    )
            
            # Get loaded model
            model_container = hf_manager.get_loaded_model(model_name)
            if not model_container:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=model_id,
                    error_message=f"Model {model_name} not loaded correctly"
                )
            
            # Convert image to PIL if needed
            if isinstance(image_data, np.ndarray):
                image = Image.fromarray(image_data.astype('uint8'))
            else:
                image = image_data
            
            # Process based on model type
            model_type = model_container.get("type", "unknown")
            
            if model_type == "vision":
                # Use vision pipeline
                pipeline = model_container["pipeline"]
                result = pipeline(image)
                
                # Extract result
                return ProcessingResult(
                    success=True,
                    modality="image",
                    model_id=model_id,
                    content={
                        "classifications": result,
                        "raw_output": result
                    }
                )
            elif model_type == "multimodal":
                # Use multimodal model directly
                model = model_container["model"]
                tokenizer = model_container["tokenizer"]
                
                # Import transformers for processing
                import torch
                from transformers import ProcessorMixin, AutoProcessor
                
                # Try to get processor
                processor = None
                try:
                    processor = AutoProcessor.from_pretrained(model_name)
                except Exception:
                    # Use tokenizer directly if no processor
                    pass
                
                # Process input
                if processor:
                    # Use processor for multimodal input
                    inputs = processor(text=prompt, images=image, return_tensors="pt").to(hf_manager.device)
                    
                    # Generate output
                    with torch.no_grad():
                        outputs = model.generate(**inputs, max_length=512)
                    
                    # Decode output
                    generated_text = processor.decode(outputs[0], skip_special_tokens=True)
                else:
                    # Manual processing for models like LLaVA
                    try:
                        from transformers import BitsAndBytesConfig
                        
                        # Use lower precision
                        bnb_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4",
                            bnb_4bit_compute_dtype=torch.float16
                        )
                        
                        # Try LLaVA-specific processing
                        from transformers import LlavaProcessor, LlavaForConditionalGeneration
                        
                        processor = LlavaProcessor.from_pretrained(model_name)
                        inputs = processor(prompt, image, return_tensors="pt").to(hf_manager.device)
                        
                        with torch.no_grad():
                            output_ids = model.generate(**inputs, max_length=512, temperature=0.7)
                        
                        generated_text = processor.decode(output_ids[0], skip_special_tokens=True)
                    except Exception as e:
                        logger.error(f"Error with specialized processing: {e}")
                        # Fallback to simple text response
                        generated_text = f"[Model {model_name} could not process the image: {str(e)}]"
                
                # Create result
                return ProcessingResult(
                    success=True,
                    modality="image",
                    model_id=model_id,
                    content={
                        "description": generated_text,
                        "prompt": prompt
                    }
                )
            else:
                return ProcessingResult.error_result(
                    modality="image",
                    model_id=model_id,
                    error_message=f"Unsupported model type: {model_type}"
                )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="image",
                model_id=model_id,
                error_message=f"Error processing with Hugging Face: {str(e)}"
            )
