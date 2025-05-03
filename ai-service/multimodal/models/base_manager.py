#!/usr/bin/env python3
"""
Base Model Manager Interface

Defines the interface for all model managers to implement. This ensures
consistent behavior across different model providers (Ollama, Hugging Face, etc.)
"""

import abc
from typing import Dict, List, Optional, Union, Any


class ModelInfo:
    """Information about a specific model."""
    
    def __init__(
        self,
        name: str,
        provider: str,
        size_mb: int,
        tags: List[str],
        version: str = "latest",
        capabilities: List[str] = None,
        loaded: bool = False,
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize model information.
        
        Args:
            name: Name of the model
            provider: Provider of the model (ollama, huggingface, etc.)
            size_mb: Size of the model in MB
            tags: List of tags describing the model
            version: Version of the model
            capabilities: List of capabilities (image, text, video, etc.)
            loaded: Whether the model is currently loaded
            metadata: Additional metadata about the model
        """
        self.name = name
        self.provider = provider
        self.size_mb = size_mb
        self.tags = tags
        self.version = version
        self.capabilities = capabilities or []
        self.loaded = loaded
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model info to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider,
            "size_mb": self.size_mb,
            "tags": self.tags,
            "version": self.version,
            "capabilities": self.capabilities,
            "loaded": self.loaded,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create model info from dictionary."""
        return cls(
            name=data["name"],
            provider=data["provider"],
            size_mb=data["size_mb"],
            tags=data["tags"],
            version=data.get("version", "latest"),
            capabilities=data.get("capabilities", []),
            loaded=data.get("loaded", False),
            metadata=data.get("metadata", {})
        )
    
    def __str__(self):
        """String representation of model info."""
        return f"{self.provider}/{self.name}:{self.version} ({self.size_mb} MB)"


class BaseModelManager(abc.ABC):
    """
    Abstract base class for model managers.
    
    This defines the interface that all model managers must implement,
    ensuring consistent behavior across different model providers.
    """
    
    @abc.abstractmethod
    def list_available_models(self) -> List[ModelInfo]:
        """
        List all available models from the provider.
        
        Returns:
            List of ModelInfo objects for available models
        """
        pass
    
    @abc.abstractmethod
    def list_installed_models(self) -> List[ModelInfo]:
        """
        List all installed models.
        
        Returns:
            List of ModelInfo objects for installed models
        """
        pass
    
    @abc.abstractmethod
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo object or None if not found
        """
        pass
    
    @abc.abstractmethod
    def download_model(self, model_name: str) -> bool:
        """
        Download a model from the provider.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is loaded in memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if loaded, False otherwise
        """
        pass
    
    def search_models(self, query: str) -> List[ModelInfo]:
        """
        Search for models matching a query.
        
        Args:
            query: Search query
            
        Returns:
            List of ModelInfo objects matching the query
        """
        # Default implementation searches model names and tags
        results = []
        query = query.lower()
        
        for model in self.list_available_models():
            if (query in model.name.lower() or 
                any(query in tag.lower() for tag in model.tags) or
                any(query in cap.lower() for cap in model.capabilities)):
                results.append(model)
        
        return results
    
    def filter_models_by_capability(self, capability: str) -> List[ModelInfo]:
        """
        Filter models by capability.
        
        Args:
            capability: Capability to filter by
            
        Returns:
            List of ModelInfo objects with the capability
        """
        return [
            model for model in self.list_available_models()
            if capability in model.capabilities
        ]
