#!/usr/bin/env python3
"""
Unified Model Manager

This module provides a unified interface for managing models from different providers.
It acts as a coordinator between specialized model managers for each provider.
"""

import os
import logging
import time
from typing import Dict, List, Optional, Union, Any, Tuple

from multimodal.models.base_manager import BaseModelManager, ModelInfo
from multimodal.utils.config import get_config, ModelConfig

# Configure logging
logger = logging.getLogger(__name__)


class UnifiedModelManager:
    """
    Unified interface for managing models from multiple providers.
    
    This class coordinates between specialized model managers for each provider,
    providing a unified interface for model discovery, selection, and management.
    """
    
    def __init__(
        self,
        providers: Optional[List[str]] = None,
        cache_dir: Optional[str] = None,
        offline_mode: bool = False,
        force_cpu: bool = False
    ):
        """
        Initialize the unified model manager.
        
        Args:
            providers: List of provider names to use (default: all available)
            cache_dir: Directory to cache models (default: provider-specific)
            offline_mode: If True, only use locally available models
            force_cpu: If True, force CPU mode even if GPU is available
        """
        self.config = get_config()
        self.offline_mode = offline_mode
        self.force_cpu = force_cpu
        self.cache_dir = cache_dir
        
        # Set up specialized model managers
        self.managers = {}
        self.available_providers = []
        
        # Set up Ollama manager if available
        try:
            from multimodal.models.ollama_manager import OllamaModelManager
            self.managers["ollama"] = OllamaModelManager()
            self.available_providers.append("ollama")
            logger.info("Initialized Ollama model manager")
        except (ImportError, Exception) as e:
            logger.warning(f"Ollama manager not available: {e}")
        
        # Set up Hugging Face manager if available
        try:
            from multimodal.models.huggingface_manager import HuggingFaceModelManager, HUGGINGFACE_AVAILABLE
            if HUGGINGFACE_AVAILABLE:
                device = "cpu" if force_cpu else None
                self.managers["huggingface"] = HuggingFaceModelManager(
                    cache_dir=cache_dir,
                    offline_mode=offline_mode,
                    device=device
                )
                self.available_providers.append("huggingface")
                logger.info("Initialized Hugging Face model manager")
            else:
                logger.warning("Hugging Face not available")
        except (ImportError, Exception) as e:
            logger.warning(f"Hugging Face manager not available: {e}")
        
        # Filter by requested providers
        if providers:
            self.active_providers = [p for p in providers if p in self.available_providers]
            if not self.active_providers:
                logger.warning(f"None of the requested providers {providers} are available")
                # Fall back to all available providers
                self.active_providers = self.available_providers
        else:
            self.active_providers = self.available_providers
        
        logger.info(f"Active model providers: {self.active_providers}")
        
        # Cache for model information
        self._model_cache = {}
        self._last_refresh = 0
        self._cache_ttl = 60  # Cache TTL in seconds
    
    def _refresh_cache(self, force: bool = False) -> None:
        """
        Refresh the model cache.
        
        Args:
            force: Force refresh even if cache is still valid
        """
        current_time = time.time()
        if force or (current_time - self._last_refresh) > self._cache_ttl:
            logger.debug("Refreshing unified model cache")
            
            # Get models from each active provider
            all_models = {}
            for provider in self.active_providers:
                if provider in self.managers:
                    try:
                        provider_models = self.managers[provider].list_available_models()
                        for model in provider_models:
                            model_id = f"{provider}/{model.name}"
                            all_models[model_id] = model
                    except Exception as e:
                        logger.error(f"Error listing models from {provider}: {e}")
            
            # Update cache
            self._model_cache = all_models
            self._last_refresh = current_time
    
    def list_available_models(self) -> List[ModelInfo]:
        """
        List all available models from all active providers.
        
        Returns:
            List of ModelInfo objects
        """
        self._refresh_cache()
        return list(self._model_cache.values())
    
    def list_active_providers(self) -> List[str]:
        """
        List all active model providers.
        
        Returns:
            List of provider names
        """
        return self.active_providers
    
    def list_models_by_provider(self, provider: str) -> List[ModelInfo]:
        """
        List all models available from a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of ModelInfo objects
        """
        self._refresh_cache()
        return [
            model for model in self._model_cache.values()
            if model.provider == provider
        ]
    
    def _make_model_id(self, provider: str, model_name: str) -> str:
        """
        Make a unified model ID from provider and model name.
        
        Args:
            provider: Provider name
            model_name: Model name
            
        Returns:
            Unified model ID
        """
        return f"{provider}/{model_name}"
    
    def _parse_model_id(self, model_id: str) -> Tuple[str, str]:
        """
        Parse a unified model ID into provider and model name.
        
        Args:
            model_id: Unified model ID
            
        Returns:
            Tuple of (provider, model_name)
        """
        if "/" in model_id:
            provider, model_name = model_id.split("/", 1)
            return provider, model_name
        
        # If no provider specified, use first available provider
        if self.active_providers:
            return self.active_providers[0], model_id
        
        # Default to empty provider
        return "", model_id
    
    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """
        Determine the provider for a given model name.
        
        Args:
            model_name: Model name or ID
            
        Returns:
            Provider name or None if not found
        """
        # If model name already includes provider, use it
        if "/" in model_name:
            provider, _ = self._parse_model_id(model_name)
            if provider in self.active_providers:
                return provider
        
        # Check config for provider information
        model_config = self.config.models.get(model_name)
        if model_config and model_config.provider in self.active_providers:
            return model_config.provider
        
        # Check each provider for model availability
        for provider in self.active_providers:
            manager = self.managers.get(provider)
            if manager and manager.is_model_available(model_name):
                return provider
        
        # Use heuristics to guess provider
        if ":" in model_name and not "/" in model_name:
            # Likely an Ollama model (format: model:tag)
            if "ollama" in self.active_providers:
                return "ollama"
        elif "/" in model_name:
            # Likely a Hugging Face model (format: org/model)
            if "huggingface" in self.active_providers:
                return "huggingface"
        
        # Default to first available provider
        if self.active_providers:
            return self.active_providers[0]
        
        return None
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_id: Model ID, either in unified format (provider/model) or provider-specific
            
        Returns:
            ModelInfo object or None if not found
        """
        self._refresh_cache()
        
        # Check if model is in cache by its full ID
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # Check if it's a full model name with provider already in cache
        for cache_id, model in self._model_cache.items():
            if model.name == model_id:
                return model
        
        # Parse model ID
        provider, model_name = self._parse_model_id(model_id)
        
        # If provider specified, use that specific manager
        if provider and provider in self.managers:
            manager = self.managers[provider]
            model_info = manager.get_model_info(model_name)
            
            if model_info:
                # Update cache
                unified_id = self._make_model_id(provider, model_name)
                self._model_cache[unified_id] = model_info
                return model_info
        
        # If no provider specified, try all active providers
        # or if specified provider did not find the model
        for try_provider in self.active_providers:
            if try_provider != provider and try_provider in self.managers:
                manager = self.managers[try_provider]
                model_info = manager.get_model_info(model_name)
                
                if model_info:
                    # Update cache
                    unified_id = self._make_model_id(try_provider, model_name)
                    self._model_cache[unified_id] = model_info
                    return model_info
                
        # Last resort: check if it's a provider-specific model ID
        # with format like 'org/model' for HuggingFace or 'model:tag' for Ollama
        if "/" in model_id and "huggingface" in self.active_providers:
            hf_manager = self.managers["huggingface"]
            model_info = hf_manager.get_model_info(model_id)
            if model_info:
                unified_id = self._make_model_id("huggingface", model_id)
                self._model_cache[unified_id] = model_info
                return model_info
        elif ":" in model_id and "ollama" in self.active_providers:
            ollama_manager = self.managers["ollama"]
            model_info = ollama_manager.get_model_info(model_id)
            if model_info:
                unified_id = self._make_model_id("ollama", model_id)
                self._model_cache[unified_id] = model_info
                return model_info
        
        return None
    
    def get_best_model_for_task(
        self,
        task_type: str,
        prefer_provider: Optional[str] = None,
        max_size_mb: Optional[int] = None
    ) -> Optional[str]:
        """
        Get the best available model for a specific task.
        
        Args:
            task_type: Type of task (image, video, text, multimodal)
            prefer_provider: Preferred provider
            max_size_mb: Maximum model size in MB
            
        Returns:
            Model ID or None if no suitable model found
        """
        self._refresh_cache()
        
        # Get all models with the required capability
        suitable_models = []
        
        for model_id, model in self._model_cache.items():
            if task_type in model.capabilities:
                if max_size_mb is None or model.size_mb <= max_size_mb:
                    suitable_models.append((model_id, model))
        
        if not suitable_models:
            logger.warning(f"No suitable models found for task {task_type}")
            return None
        
        # Sort models by preference
        def model_score(model_item):
            model_id, model = model_item
            score = 0
            
            # Prefer models from preferred provider
            if prefer_provider and model.provider == prefer_provider:
                score += 100
            
            # Prefer locally available models
            provider, model_name = self._parse_model_id(model_id)
            if provider in self.managers and self.managers[provider].is_model_available(model_name):
                score += 50
            
            # Adjust score based on model size (prefer smaller models)
            score -= model.size_mb / 1000
            
            return score
        
        suitable_models.sort(key=model_score, reverse=True)
        
        # Return the best model ID
        if suitable_models:
            return suitable_models[0][0]
        
        return None
    
    def download_model(self, model_id: str) -> bool:
        """
        Download a model from its provider.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.offline_mode:
            logger.error("Cannot download models in offline mode")
            return False
        
        provider, model_name = self._parse_model_id(model_id)
        
        if provider not in self.managers:
            logger.error(f"Provider {provider} not available")
            return False
        
        logger.info(f"Downloading model {model_name} from {provider}")
        return self.managers[provider].download_model(model_name)
    
    def load_model(self, model_id: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if successful, False otherwise
        """
        provider, model_name = self._parse_model_id(model_id)
        
        if provider not in self.managers:
            logger.error(f"Provider {provider} not available")
            return False
        
        logger.info(f"Loading model {model_name} from {provider}")
        return self.managers[provider].load_model(model_name)
    
    def unload_model(self, model_id: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if successful, False otherwise
        """
        provider, model_name = self._parse_model_id(model_id)
        
        if provider not in self.managers:
            logger.error(f"Provider {provider} not available")
            return False
        
        logger.info(f"Unloading model {model_name} from {provider}")
        return self.managers[provider].unload_model(model_name)
    
    def is_model_available(self, model_id: str) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if available, False otherwise
        """
        provider, model_name = self._parse_model_id(model_id)
        
        if provider not in self.managers:
            return False
        
        return self.managers[provider].is_model_available(model_name)
    
    def is_model_loaded(self, model_id: str) -> bool:
        """
        Check if a model is loaded in memory.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if loaded, False otherwise
        """
        provider, model_name = self._parse_model_id(model_id)
        
        if provider not in self.managers:
            return False
        
        return self.managers[provider].is_model_loaded(model_name)
    
    def get_loaded_model(self, model_id: str) -> Optional[Any]:
        """
        Get a loaded model for direct use.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model object or None if not loaded
        """
        provider, model_name = self._parse_model_id(model_id)
        
        if provider != "huggingface" or provider not in self.managers:
            logger.error(f"Direct model access not supported for provider {provider}")
            return None
        
        try:
            return self.managers[provider].get_loaded_model(model_name)
        except Exception as e:
            logger.error(f"Error getting loaded model: {e}")
            return None
    
    def search_models(self, query: str) -> List[ModelInfo]:
        """
        Search for models matching a query across all providers.
        
        Args:
            query: Search query
            
        Returns:
            List of ModelInfo objects matching the query
        """
        self._refresh_cache()
        
        results = []
        query = query.lower()
        
        for model_id, model in self._model_cache.items():
            if (query in model_id.lower() or
                query in model.name.lower() or
                any(query in tag.lower() for tag in model.tags) or
                any(query in cap.lower() for cap in model.capabilities)):
                results.append(model)
        
        return results
    
    def filter_models(
        self,
        providers: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        max_size_mb: Optional[int] = None,
        installed_only: bool = False
    ) -> List[ModelInfo]:
        """
        Filter models based on criteria.
        
        Args:
            providers: List of providers to include
            capabilities: List of required capabilities
            tags: List of required tags
            max_size_mb: Maximum model size in MB
            installed_only: If True, only include installed models
            
        Returns:
            List of ModelInfo objects matching the criteria
        """
        self._refresh_cache()
        
        results = []
        
        for model_id, model in self._model_cache.items():
            # Filter by provider
            if providers and model.provider not in providers:
                continue
            
            # Filter by capabilities
            if capabilities and not all(cap in model.capabilities for cap in capabilities):
                continue
            
            # Filter by tags
            if tags and not all(tag in model.tags for tag in tags):
                continue
            
            # Filter by size
            if max_size_mb is not None and model.size_mb > max_size_mb:
                continue
            
            # Filter by installation status
            if installed_only:
                provider, model_name = self._parse_model_id(model_id)
                if provider not in self.managers or not self.managers[provider].is_model_available(model_name):
                    continue
            
            results.append(model)
        
        return results
    
    def get_manager_for_provider(self, provider: str) -> Optional[BaseModelManager]:
        """
        Get the specialized model manager for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            BaseModelManager instance or None if not available
        """
        return self.managers.get(provider)
    
    def ensure_model_availability(self, model_id: str) -> bool:
        """
        Ensure that a model is available locally, downloading if necessary.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if model is available, False otherwise
        """
        if self.is_model_available(model_id):
            return True
        
        if self.offline_mode:
            logger.error(f"Model {model_id} not available and offline mode is enabled")
            return False
        
        return self.download_model(model_id)
    
    def check_resource_availability(self, required_memory_gb: float) -> bool:
        """
        Check if the system has enough resources to load a model.
        
        Args:
            required_memory_gb: Required memory in GB
            
        Returns:
            True if resources are available, False otherwise
        """
        try:
            import psutil
            # Get available memory in GB
            available_memory_gb = psutil.virtual_memory().available / (1024 * 1024 * 1024)
            return available_memory_gb >= required_memory_gb
        except ImportError:
            logger.warning("psutil not available, cannot check resource availability")
            # Assume resources are available if we can't check
            return True
    
    def unload_all_models(self, provider: Optional[str] = None) -> None:
        """
        Unload all loaded models, optionally filtered by provider.
        
        Args:
            provider: Provider to unload models from (optional)
        """
        logger.info(f"Unloading all models{f' from {provider}' if provider else ''}")
        
        # Get list of currently loaded models
        models_to_unload = []
        for model_id in self._model_cache:
            model = self._model_cache[model_id]
            if model.loaded and (provider is None or model.provider == provider):
                models_to_unload.append(model_id)
        
        # Unload models
        for model_id in models_to_unload:
            try:
                self.unload_model(model_id)
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear CUDA cache if available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache")
        except (ImportError, AttributeError):
            pass
