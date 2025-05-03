#!/usr/bin/env python3
"""
Ollama Model Manager

Implements the BaseModelManager interface for Ollama models.
Handles listing, downloading, loading, and managing Ollama models.
"""

import os
import json
import logging
import subprocess
from typing import Dict, List, Optional, Union, Any
import httpx
import time

from multimodal.models.base_manager import BaseModelManager, ModelInfo

# Configure logging
logger = logging.getLogger(__name__)

# Default Ollama API URL
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


class OllamaModelManager(BaseModelManager):
    """
    Model manager for Ollama models.
    
    This class handles interaction with the Ollama API for model management.
    """
    
    def __init__(self, ollama_host: Optional[str] = None, timeout: int = 30):
        """
        Initialize Ollama model manager.
        
        Args:
            ollama_host: URL of Ollama API (default: environment variable or localhost)
            timeout: Timeout for API calls in seconds
        """
        self.ollama_host = ollama_host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        logger.info(f"Initialized Ollama model manager with host {self.ollama_host}")
        
        # Cache of model information
        self._model_info_cache = {}
        self._last_refresh = 0
        self._cache_ttl = 60  # Cache TTL in seconds
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Ollama API.
        
        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint
            data: Request data
            
        Returns:
            API response as dictionary
        """
        url = f"{self.ollama_host}/api/{endpoint}"
        
        try:
            if method.lower() == "get":
                response = self.client.get(url)
            elif method.lower() == "post":
                response = self.client.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ollama API: {e}")
            return {"error": "Invalid JSON response"}
    
    def _ensure_ollama_running(self) -> bool:
        """
        Ensure that the Ollama service is running.
        
        Returns:
            True if Ollama is running, False otherwise
        """
        try:
            response = self.client.get(f"{self.ollama_host}", timeout=2)
            return response.status_code == 200
        except httpx.HTTPError:
            logger.warning("Ollama service not responding, attempting to start it")
            
            # Try to start Ollama
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                
                # Wait for Ollama to start
                for _ in range(5):
                    time.sleep(2)
                    try:
                        response = self.client.get(f"{self.ollama_host}", timeout=2)
                        if response.status_code == 200:
                            logger.info("Ollama service started successfully")
                            return True
                    except httpx.HTTPError:
                        pass
                
                logger.error("Failed to start Ollama service")
                return False
            except Exception as e:
                logger.error(f"Error starting Ollama service: {e}")
                return False
    
    def _refresh_model_cache(self, force: bool = False) -> None:
        """
        Refresh the model information cache.
        
        Args:
            force: Force refresh even if cache is still valid
        """
        current_time = time.time()
        if force or (current_time - self._last_refresh) > self._cache_ttl:
            logger.debug("Refreshing model cache")
            self._model_info_cache = {}
            models = self.list_installed_models()
            for model in models:
                self._model_info_cache[model.name] = model
            self._last_refresh = current_time
    
    def _parse_model_info(self, model_data: Dict) -> ModelInfo:
        """
        Parse model information from Ollama API response.
        
        Args:
            model_data: Model data from Ollama API
            
        Returns:
            ModelInfo object
        """
        name = model_data.get("name", "")
        
        # Extract tags from model name (format: name:tag)
        parts = name.split(":")
        model_name = parts[0]
        version = parts[1] if len(parts) > 1 else "latest"
        
        # Get model size
        size_mb = int(model_data.get("size", 0) / (1024 * 1024))
        
        # Determine capabilities
        capabilities = []
        # We need to make an informed guess about capabilities since Ollama doesn't provide this info directly
        tags = model_data.get("tags", [])
        
        if "vision" in name.lower() or "multimodal" in name.lower():
            capabilities.extend(["image", "text"])
            tags.extend(["vision", "multimodal"])
        
        if "video" in name.lower():
            capabilities.append("video")
            tags.append("video")
        
        # Add default capability
        if not capabilities:
            capabilities.append("text")
            tags.append("text")
        
        # Check if model is currently loaded
        loaded = model_data.get("status", "") == "loaded"
        
        return ModelInfo(
            name=name,
            provider="ollama",
            size_mb=size_mb,
            tags=tags,
            version=version,
            capabilities=capabilities,
            loaded=loaded,
            metadata=model_data
        )
    
    def list_available_models(self) -> List[ModelInfo]:
        """
        List all available models from Ollama.
        This includes both installed models and models available for download.
        
        Returns:
            List of ModelInfo objects
        """
        if not self._ensure_ollama_running():
            logger.error("Ollama service not running")
            return []
        
        # Get installed models
        installed_models = self.list_installed_models()
        
        # Also get registry models (would require additional API call)
        # This is not yet implemented in Ollama API
        
        return installed_models
    
    def list_installed_models(self) -> List[ModelInfo]:
        """
        List all installed models.
        
        Returns:
            List of ModelInfo objects
        """
        if not self._ensure_ollama_running():
            logger.error("Ollama service not running")
            return []
        
        response = self._make_request("get", "tags")
        
        if "error" in response:
            logger.error(f"Error listing models: {response['error']}")
            return []
        
        models = response.get("models", [])
        return [self._parse_model_info(model) for model in models]
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo object or None if not found
        """
        self._refresh_model_cache()
        
        # Check if model is in cache
        if model_name in self._model_info_cache:
            return self._model_info_cache[model_name]
        
        # If not in cache, check if it's installed
        for model in self.list_installed_models():
            if model.name == model_name:
                self._model_info_cache[model_name] = model
                return model
        
        return None
    
    def download_model(self, model_name: str) -> bool:
        """
        Download a model from Ollama.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_ollama_running():
            logger.error("Ollama service not running")
            return False
        
        logger.info(f"Downloading Ollama model: {model_name}")
        
        response = self._make_request("post", "pull", {"name": model_name})
        
        if "error" in response:
            logger.error(f"Error downloading model: {response['error']}")
            return False
        
        # Force refresh cache
        self._refresh_model_cache(force=True)
        
        return True
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_ollama_running():
            logger.error("Ollama service not running")
            return False
        
        if not self.is_model_available(model_name):
            logger.error(f"Model {model_name} not available, try downloading it first")
            return False
        
        logger.info(f"Loading Ollama model: {model_name}")
        
        # Ollama loads models on first use, so we just need to check if it's available
        response = self._make_request("post", "generate", {
            "model": model_name,
            "prompt": "Test loading model. Respond with exactly one word: 'LOADED'",
            "stream": False
        })
        
        if "error" in response:
            logger.error(f"Error loading model: {response['error']}")
            return False
        
        # Force refresh cache
        self._refresh_model_cache(force=True)
        
        return "LOADED" in response.get("response", "")
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Ollama doesn't support explicit unloading, but we can try to clean
        up resources by triggering garbage collection.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_ollama_running():
            logger.error("Ollama service not running")
            return False
        
        # No explicit unload in Ollama, but we can update our cache
        if model_name in self._model_info_cache:
            model = self._model_info_cache[model_name]
            model.loaded = False
        
        return True
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if available, False otherwise
        """
        model_info = self.get_model_info(model_name)
        return model_info is not None
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is loaded in memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if loaded, False otherwise
        """
        model_info = self.get_model_info(model_name)
        if model_info is None:
            return False
        
        return model_info.loaded
