#!/usr/bin/env python3
"""
Base Multimodal Processor Interface

Defines the interface for all multimodal processors to implement.
This ensures consistent behavior across different modality processors.
"""

import abc
import logging
from typing import Dict, List, Optional, Union, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)


class ProcessingResult:
    """Container for multimodal processing results."""
    
    def __init__(
        self,
        success: bool,
        modality: str,
        model_id: str,
        content: Dict[str, Any],
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize processing result.
        
        Args:
            success: Whether processing was successful
            modality: Type of modality processed (image, video, text, multimodal)
            model_id: ID of the model used for processing
            content: Processing result content
            error: Error message if processing failed
            metadata: Additional metadata about the processing
        """
        self.success = success
        self.modality = modality
        self.model_id = model_id
        self.content = content
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = self.metadata.get("timestamp", None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "modality": self.modality,
            "model_id": self.model_id,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingResult':
        """Create result from dictionary."""
        return cls(
            success=data["success"],
            modality=data["modality"],
            model_id=data["model_id"],
            content=data["content"],
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def error_result(cls, modality: str, model_id: str, error_message: str) -> 'ProcessingResult':
        """Create an error result."""
        return cls(
            success=False,
            modality=modality,
            model_id=model_id,
            content={},
            error=error_message
        )


class BaseProcessor(abc.ABC):
    """
    Abstract base class for multimodal processors.
    
    This defines the interface that all processors must implement,
    ensuring consistent behavior across different modalities.
    """
    
    @abc.abstractmethod
    def process(self, data: Any, model_id: Optional[str] = None, **kwargs) -> ProcessingResult:
        """
        Process input data using specified model.
        
        Args:
            data: Input data to process
            model_id: ID of model to use for processing
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult object with results
        """
        pass
    
    @abc.abstractmethod
    def get_default_model_id(self) -> str:
        """
        Get default model ID for this processor.
        
        Returns:
            Default model ID
        """
        pass
    
    @abc.abstractmethod
    def get_modality(self) -> str:
        """
        Get modality type of this processor.
        
        Returns:
            Modality type (image, video, text, multimodal)
        """
        pass
    
    @abc.abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """
        Check if processor supports a specific model.
        
        Args:
            model_id: Model ID to check
            
        Returns:
            True if supported, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get supported input formats.
        
        Returns:
            List of supported format identifiers
        """
        pass
    
    def validate_input(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input data.
        
        Args:
            data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Base implementation always validates
        return True, None
