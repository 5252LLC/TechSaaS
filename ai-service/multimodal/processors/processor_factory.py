#!/usr/bin/env python3
"""
Multimodal Processor Factory

Factory class for creating and managing different types of processors
based on modality and input format.
"""

import os
import logging
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type, Tuple

from multimodal.processors.base_processor import BaseProcessor, ProcessingResult
from multimodal.models.unified_manager import UnifiedModelManager
from multimodal.utils.config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class ProcessorFactory:
    """
    Factory for creating and managing multimodal processors.
    
    This class is responsible for determining the appropriate processor
    for a given input and coordinating between different processors.
    """
    
    def __init__(self, model_manager: Optional[UnifiedModelManager] = None):
        """
        Initialize processor factory.
        
        Args:
            model_manager: Unified model manager to use for models
        """
        self.config = get_config()
        self.model_manager = model_manager or UnifiedModelManager()
        
        # Initialize processor registry
        self._processors: Dict[str, BaseProcessor] = {}
        self._format_mapping: Dict[str, str] = {}
        self._extension_mapping: Dict[str, str] = {}
        self._mimetype_mapping: Dict[str, str] = {}
        
        # Initialize mimetypes
        if not mimetypes.inited:
            mimetypes.init()
    
    def register_processor(self, processor: BaseProcessor) -> None:
        """
        Register a processor with the factory.
        
        Args:
            processor: Processor to register
        """
        modality = processor.get_modality()
        
        # Register processor for its modality
        self._processors[modality] = processor
        
        # Register supported formats
        for format_id in processor.get_supported_formats():
            self._format_mapping[format_id] = modality
            
            # If format is a file extension, register it
            if format_id.startswith('.'):
                self._extension_mapping[format_id] = modality
            
            # If format is a mimetype, register it
            if '/' in format_id:
                self._mimetype_mapping[format_id] = modality
        
        logger.info(f"Registered {modality} processor with {len(processor.get_supported_formats())} supported formats")
    
    def get_processor(self, modality: str) -> Optional[BaseProcessor]:
        """
        Get processor for a specific modality.
        
        Args:
            modality: Modality type (image, video, text, multimodal)
            
        Returns:
            Processor instance or None if not found
        """
        return self._processors.get(modality)
    
    def get_processor_for_input(self, input_data: Any) -> Optional[BaseProcessor]:
        """
        Determine the appropriate processor for input data.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Appropriate processor or None if not found
        """
        # Handle string input (text or file path)
        if isinstance(input_data, str):
            # Check if input looks like a file path
            if os.path.exists(input_data):
                return self.get_processor_for_file(input_data)
            else:
                # Assume it's text
                return self.get_processor("text")
        
        # Handle file-like objects
        if hasattr(input_data, 'read') and callable(input_data.read):
            # Try to determine mimetype from name if available
            if hasattr(input_data, 'name'):
                mimetype, _ = mimetypes.guess_type(input_data.name)
                if mimetype:
                    return self.get_processor_for_mimetype(mimetype)
            
            # Default to text for file-like objects
            return self.get_processor("text")
        
        # Handle Path objects
        if isinstance(input_data, Path):
            return self.get_processor_for_file(str(input_data))
        
        # Handle dictionaries (potentially multimodal)
        if isinstance(input_data, dict):
            if 'image' in input_data and 'text' in input_data:
                return self.get_processor("multimodal")
            elif 'image' in input_data:
                return self.get_processor("image")
            elif 'video' in input_data:
                return self.get_processor("video")
            elif 'text' in input_data:
                return self.get_processor("text")
        
        # Default to text for unknown input
        logger.warning(f"Could not determine processor for input type {type(input_data)}")
        return self.get_processor("text")
    
    def get_processor_for_file(self, file_path: str) -> Optional[BaseProcessor]:
        """
        Get processor for a file based on extension and content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Appropriate processor or None if not found
        """
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Get file extension
        _, extension = os.path.splitext(file_path.lower())
        
        # Try to match by extension
        if extension in self._extension_mapping:
            modality = self._extension_mapping[extension]
            return self.get_processor(modality)
        
        # Try to match by mimetype
        mimetype, _ = mimetypes.guess_type(file_path)
        if mimetype:
            processor = self.get_processor_for_mimetype(mimetype)
            if processor:
                return processor
        
        # Try to detect based on content
        # Here we could add more sophisticated content detection
        # For now, use simple heuristics
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
                
                # Check for image formats
                if header.startswith(b'\xff\xd8\xff'):  # JPEG
                    return self.get_processor("image")
                elif header.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                    return self.get_processor("image")
                elif header.startswith(b'GIF8'):  # GIF
                    return self.get_processor("image")
                elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':  # WEBP
                    return self.get_processor("image")
                
                # Check for video formats
                if header.startswith(b'\x00\x00\x00\x18ftypmp42'):  # MP4
                    return self.get_processor("video")
                elif header.startswith(b'\x00\x00\x00\x1cftypisom'):  # MP4
                    return self.get_processor("video")
        except Exception as e:
            logger.warning(f"Error examining file content: {e}")
        
        # Default based on general mimetype category
        if mimetype:
            if mimetype.startswith('image/'):
                return self.get_processor("image")
            elif mimetype.startswith('video/'):
                return self.get_processor("video")
            elif mimetype.startswith('text/') or mimetype in ('application/json', 'application/xml'):
                return self.get_processor("text")
        
        logger.warning(f"Could not determine processor for file: {file_path}")
        return None
    
    def get_processor_for_mimetype(self, mimetype: str) -> Optional[BaseProcessor]:
        """
        Get processor for a specific mimetype.
        
        Args:
            mimetype: MIME type string
            
        Returns:
            Appropriate processor or None if not found
        """
        # Direct mimetype match
        if mimetype in self._mimetype_mapping:
            modality = self._mimetype_mapping[mimetype]
            return self.get_processor(modality)
        
        # Category match
        if mimetype.startswith('image/'):
            return self.get_processor("image")
        elif mimetype.startswith('video/'):
            return self.get_processor("video")
        elif mimetype.startswith('text/') or mimetype in ('application/json', 'application/xml'):
            return self.get_processor("text")
        
        logger.warning(f"Could not determine processor for mimetype: {mimetype}")
        return None
    
    def process(
        self, 
        input_data: Any, 
        model_id: Optional[str] = None,
        modality: Optional[str] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Process input data using appropriate processor.
        
        Args:
            input_data: Input data to process
            model_id: ID of model to use (optional)
            modality: Force specific modality processor (optional)
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with results or error
        """
        # Determine processor to use
        processor = None
        if modality:
            # Use specified modality
            processor = self.get_processor(modality)
            if not processor:
                error_msg = f"No processor available for modality: {modality}"
                logger.error(error_msg)
                return ProcessingResult.error_result(
                    modality=modality or "unknown",
                    model_id=model_id or "none",
                    error_message=error_msg
                )
        else:
            # Automatically determine processor
            processor = self.get_processor_for_input(input_data)
            if not processor:
                error_msg = f"Could not determine appropriate processor for input"
                logger.error(error_msg)
                return ProcessingResult.error_result(
                    modality="unknown",
                    model_id=model_id or "none",
                    error_message=error_msg
                )
        
        # Determine model to use
        actual_model_id = model_id
        if not actual_model_id:
            # Use default model for processor
            actual_model_id = processor.get_default_model_id()
        
        # Process input
        try:
            logger.info(f"Processing with {processor.get_modality()} processor using model {actual_model_id}")
            return processor.process(input_data, actual_model_id, **kwargs)
        except Exception as e:
            error_msg = f"Error processing input: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ProcessingResult.error_result(
                modality=processor.get_modality(),
                model_id=actual_model_id,
                error_message=error_msg
            )
    
    def get_supported_modalities(self) -> List[str]:
        """
        Get list of supported modalities.
        
        Returns:
            List of modality names
        """
        return list(self._processors.keys())
    
    def get_supported_formats(self, modality: Optional[str] = None) -> List[str]:
        """
        Get list of supported formats, optionally filtered by modality.
        
        Args:
            modality: Filter by modality (optional)
            
        Returns:
            List of format identifiers
        """
        if modality:
            processor = self.get_processor(modality)
            if processor:
                return processor.get_supported_formats()
            return []
        
        # Get all formats
        formats = []
        for processor in self._processors.values():
            formats.extend(processor.get_supported_formats())
        return formats
    
    def get_default_model_for_modality(self, modality: str) -> Optional[str]:
        """
        Get default model for a modality.
        
        Args:
            modality: Modality type
            
        Returns:
            Model ID or None if not available
        """
        processor = self.get_processor(modality)
        if processor:
            return processor.get_default_model_id()
        return None
