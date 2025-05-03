#!/usr/bin/env python3
"""
Text Processor

Implements the BaseProcessor interface for text processing.
Handles preprocessing and analysis of text using various models.
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

# Configure logging
logger = logging.getLogger(__name__)

# Supported text formats
SUPPORTED_TEXT_FORMATS = [
    # Common file extensions
    '.txt', '.md', '.json', '.xml', '.csv', '.html', '.htm',
    
    # MIME types
    'text/plain', 'text/markdown', 'application/json', 
    'text/csv', 'text/html', 'application/xml'
]


class TextProcessor(BaseProcessor):
    """
    Processor for text data.
    
    This processor handles preprocessing and analysis of text data
    using various models from different providers.
    """
    
    def __init__(
        self, 
        model_manager: Optional[UnifiedModelManager] = None,
        default_model_id: Optional[str] = None
    ):
        """
        Initialize text processor.
        
        Args:
            model_manager: Model manager for accessing models
            default_model_id: Default model ID to use
        """
        from multimodal.utils.config import get_config
        self.config = get_config()
        self.model_manager = model_manager or UnifiedModelManager()
        self.default_model_id = default_model_id or self.config.default_text_model
        
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
        return "text"
    
    def get_supported_formats(self) -> List[str]:
        """Get supported input formats."""
        return SUPPORTED_TEXT_FORMATS
    
    def supports_model(self, model_id: str) -> bool:
        """Check if processor supports a specific model."""
        # Extract model info
        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            return False
        
        # Check if model has text capability
        return "text" in model_info.capabilities
    
    def load_text(self, text_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Load text from file path.
        
        Args:
            text_path: Path to text file
            
        Returns:
            Tuple of (text_content, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(text_path):
                return None, f"Text file not found: {text_path}"
            
            # Check file size to avoid loading extremely large files
            file_size = os.path.getsize(text_path)
            max_size = self.config.processing.max_file_size_mb * 1024 * 1024
            if file_size > max_size:
                return None, f"File too large: {file_size / (1024 * 1024):.2f} MB (max {self.config.processing.max_file_size_mb} MB)"
            
            # Try to detect encoding
            encoding = 'utf-8'
            
            # Read file with detected encoding
            with open(text_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return content, None
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(text_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content, None
            except Exception as e:
                return None, f"Error decoding file: {str(e)}"
        except Exception as e:
            return None, f"Error loading text file: {str(e)}"
    
    def preprocess_text(
        self, 
        text: str,
        max_length: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """
        Preprocess text for model input.
        
        Args:
            text: Text content to process
            max_length: Maximum length in tokens (approximate)
            **kwargs: Additional preprocessing options
            
        Returns:
            Tuple of (processed_text, metadata, error_message)
        """
        try:
            # Initialize metadata
            metadata = {
                "original_length": len(text),
                "original_word_count": len(text.split())
            }
            
            # Trim if too long
            if max_length and len(text) > max_length:
                # Simple truncation for now
                # In a real implementation, we would use a more sophisticated
                # approach like a sliding window or recursive summarization
                text = text[:max_length]
                metadata["truncated"] = True
                metadata["truncated_length"] = len(text)
            
            # Additional preprocessing
            if kwargs.get("lowercase", False):
                text = text.lower()
                metadata["lowercased"] = True
            
            if kwargs.get("normalize_whitespace", False):
                import re
                text = re.sub(r'\s+', ' ', text).strip()
                metadata["normalized_whitespace"] = True
            
            return text, metadata, None
        except Exception as e:
            return text, {}, f"Error preprocessing text: {str(e)}"
    
    def validate_input(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if input is a string (content or path)
        if isinstance(data, str):
            if os.path.exists(data):
                # It's a file path
                file_size = os.path.getsize(data)
                max_size = self.config.processing.max_file_size_mb * 1024 * 1024
                if file_size > max_size:
                    return False, f"File too large: {file_size / (1024 * 1024):.2f} MB (max {self.config.processing.max_file_size_mb} MB)"
            else:
                # It's a text string, check length
                if len(data) > self.config.processing.max_text_length:
                    return False, f"Text too long: {len(data)} chars (max {self.config.processing.max_text_length})"
        # Check if input is a file-like object
        elif hasattr(data, 'read') and callable(getattr(data, 'read')):
            # It's a file-like object, check if it has a name attribute
            if hasattr(data, 'name') and os.path.exists(data.name):
                file_size = os.path.getsize(data.name)
                max_size = self.config.processing.max_file_size_mb * 1024 * 1024
                if file_size > max_size:
                    return False, f"File too large: {file_size / (1024 * 1024):.2f} MB (max {self.config.processing.max_file_size_mb} MB)"
        else:
            return False, f"Unsupported input type: {type(data)}"
        
        return True, None
    
    def process(
        self, 
        data: Any, 
        model_id: Optional[str] = None,
        prompt_template: Optional[str] = None,
        return_raw_output: bool = False,
        **kwargs
    ) -> ProcessingResult:
        """
        Process text data using specified model.
        
        Args:
            data: Input text data (string or file path)
            model_id: ID of model to use
            prompt_template: Optional template for prompt
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
                modality="text",
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
                        modality="text",
                        model_id=actual_model_id,
                        error_message=f"Model {actual_model_id} not available and could not be downloaded"
                    )
            except Exception as e:
                return ProcessingResult.error_result(
                    modality="text",
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
                        modality="text",
                        model_id=actual_model_id,
                        error_message=f"Insufficient memory to load model {actual_model_id}, even after unloading other models"
                    )
        
        # After this point, we should have enough resources to load the model
        
        # Prepare input
        try:
            # Process input
            text_data = data
            
            # For string inputs that are paths, load the text
            if isinstance(data, str) and os.path.exists(data):
                text_content, error = self.load_text(data)
                if error:
                    return ProcessingResult.error_result(
                        modality="text",
                        model_id=actual_model_id,
                        error_message=error
                    )
                text_data = text_content
            
            # Preprocess text
            max_length = kwargs.get("max_length", self.config.processing.max_text_length)
            text_data, preprocess_metadata, preprocess_error = self.preprocess_text(
                text_data, max_length=max_length, **kwargs
            )
            
            if preprocess_error:
                logger.warning(f"Text preprocessing warning: {preprocess_error}")
            
            # Parse model_id to get provider and name
            provider = self.model_manager.get_provider_for_model(actual_model_id)
            if not provider:
                return ProcessingResult.error_result(
                    modality="text",
                    model_id=actual_model_id,
                    error_message=f"Could not determine provider for model {actual_model_id}"
                )
            
            # Process based on provider
            if provider == "ollama":
                result = self._process_with_ollama(text_data, actual_model_id, prompt_template, **kwargs)
            elif provider == "huggingface":
                result = self._process_with_huggingface(text_data, actual_model_id, prompt_template, **kwargs)
            else:
                return ProcessingResult.error_result(
                    modality="text",
                    model_id=actual_model_id,
                    error_message=f"Unsupported provider: {provider}"
                )
            
            # Add metadata
            processing_time = time.time() - start_time
            result.metadata["processing_time"] = processing_time
            result.metadata["timestamp"] = datetime.now().isoformat()
            result.metadata.update(preprocess_metadata)
            
            # Remove raw output if not requested
            if not return_raw_output and "raw_output" in result.content:
                del result.content["raw_output"]
            
            return result
        except Exception as e:
            error_msg = f"Error processing text: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ProcessingResult.error_result(
                modality="text",
                model_id=actual_model_id,
                error_message=error_msg
            )
    
    def _process_with_ollama(
        self, 
        text_data: str,
        model_id: str,
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Process text with Ollama model.
        
        Args:
            text_data: Text content to process
            model_id: Full model ID including provider
            prompt_template: Optional template for prompt
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            import httpx
            
            # Get Ollama manager
            ollama_manager = self.model_manager.get_manager_for_provider("ollama")
            if not ollama_manager:
                return ProcessingResult.error_result(
                    modality="text",
                    model_id=model_id,
                    error_message="Ollama manager not available"
                )
            
            # Extract model name from model_id
            _, model_name = self.model_manager._parse_model_id(model_id)
            
            # Prepare prompt
            if prompt_template:
                # Using a template like "{text}"
                prompt = prompt_template.format(text=text_data)
            else:
                prompt = text_data
            
            # Prepare request
            endpoint = f"{ollama_manager.ollama_host}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": kwargs.get("options", {})
            }
            
            # Make request
            response = httpx.post(endpoint, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            
            # Extract response
            model_output = result.get("response", "")
            
            # Extract task-specific data
            task = kwargs.get("task", "generation")
            content = {"text": model_output, "prompt": prompt, "raw_output": result}
            
            if task == "summarization":
                content["summary"] = model_output
            elif task == "classification":
                # Try to parse output as a class
                content["classification"] = model_output.strip()
            
            # Create result
            return ProcessingResult(
                success=True,
                modality="text",
                model_id=model_id,
                content=content
            )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="text",
                model_id=model_id,
                error_message=f"Error processing with Ollama: {str(e)}"
            )
    
    def _process_with_huggingface(
        self, 
        text_data: str,
        model_id: str,
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Process text with Hugging Face model.
        
        Args:
            text_data: Text content to process
            model_id: Full model ID including provider
            prompt_template: Optional template for prompt
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results
        """
        try:
            # Get Hugging Face manager
            hf_manager = self.model_manager.get_manager_for_provider("huggingface")
            if not hf_manager:
                return ProcessingResult.error_result(
                    modality="text",
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
                        modality="text",
                        model_id=model_id,
                        error_message=f"Failed to load model {model_name}"
                    )
            
            # Get loaded model
            model_container = hf_manager.get_loaded_model(model_name)
            if not model_container:
                return ProcessingResult.error_result(
                    modality="text",
                    model_id=model_id,
                    error_message=f"Model {model_name} not loaded correctly"
                )
            
            # Prepare prompt
            if prompt_template:
                # Using a template like "{text}"
                prompt = prompt_template.format(text=text_data)
            else:
                prompt = text_data
            
            # Process using pipeline
            pipeline = model_container.get("pipeline")
            if not pipeline:
                return ProcessingResult.error_result(
                    modality="text",
                    model_id=model_id,
                    error_message=f"No pipeline available for model {model_name}"
                )
            
            # Process based on task
            task = kwargs.get("task", "generation")
            max_length = kwargs.get("max_length", 512)
            
            if task == "summarization":
                result = pipeline(prompt, max_length=max_length, min_length=20)
                return ProcessingResult(
                    success=True,
                    modality="text",
                    model_id=model_id,
                    content={
                        "summary": result[0]["summary_text"],
                        "prompt": prompt,
                        "raw_output": result
                    }
                )
            elif task == "classification":
                result = pipeline(prompt)
                return ProcessingResult(
                    success=True,
                    modality="text",
                    model_id=model_id,
                    content={
                        "classification": result[0]["label"],
                        "score": result[0]["score"],
                        "prompt": prompt,
                        "raw_output": result
                    }
                )
            else:  # Default to generation
                result = pipeline(prompt, max_length=max_length)
                return ProcessingResult(
                    success=True,
                    modality="text",
                    model_id=model_id,
                    content={
                        "text": result[0]["generated_text"],
                        "prompt": prompt,
                        "raw_output": result
                    }
                )
        except Exception as e:
            return ProcessingResult.error_result(
                modality="text",
                model_id=model_id,
                error_message=f"Error processing with Hugging Face: {str(e)}"
            )
