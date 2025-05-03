#!/usr/bin/env python3
"""
Hugging Face Model Manager

Implements the BaseModelManager interface for Hugging Face models.
Handles listing, downloading, loading, and managing Hugging Face models.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set
import time
import shutil

# Import optional dependencies with graceful fallback
try:
    import torch
    import transformers
    from transformers import AutoConfig, AutoModel, AutoTokenizer
    from transformers import pipeline
    from huggingface_hub import (
        HfApi, 
        HfFolder, 
        ModelFilter,
        scan_cache_dir, 
        list_models, 
        login, 
        logout
    )
    from huggingface_hub.utils import HfHubHTTPError
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Hugging Face packages not installed, functionality will be limited")

from multimodal.models.base_manager import BaseModelManager, ModelInfo

# Configure logging
logger = logging.getLogger(__name__)

# Default cache directory
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/huggingface")


class HuggingFaceModelManager(BaseModelManager):
    """
    Model manager for Hugging Face models.
    
    This class handles interaction with the Hugging Face Hub and Transformers library.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        use_auth_token: Optional[str] = None,
        device: Optional[str] = None,
        offline_mode: bool = False
    ):
        """
        Initialize Hugging Face model manager.
        
        Args:
            cache_dir: Directory to cache models (default: ~/.cache/huggingface)
            use_auth_token: Hugging Face token for private models
            device: Device to use for loading models (cpu, cuda, mps)
            offline_mode: If True, only use locally available models
        """
        if not HUGGINGFACE_AVAILABLE:
            logger.error("Hugging Face packages not installed")
            raise ImportError(
                "Hugging Face packages are required. "
                "Install with pip install transformers huggingface_hub"
            )
        
        self.cache_dir = cache_dir or os.environ.get("HF_HOME", DEFAULT_CACHE_DIR)
        self.auth_token = use_auth_token or os.environ.get("HF_TOKEN")
        self.offline_mode = offline_mode
        
        # Set device
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch, "backends") and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        
        logger.info(f"Initialized Hugging Face model manager with device {self.device}")
        
        # Initialize Hugging Face API
        self.api = HfApi()
        
        # Initialize cache structures
        self._models_cache = {}
        self._loaded_models = {}
        self._last_refresh = 0
        self._cache_ttl = 300  # Cache TTL in seconds
        
        # Try to authenticate if token is provided
        if self.auth_token and not offline_mode:
            try:
                login(token=self.auth_token)
                logger.info("Authenticated with Hugging Face Hub")
            except Exception as e:
                logger.warning(f"Failed to authenticate with Hugging Face Hub: {e}")
    
    def _get_model_capabilities(self, model_id: str, model_config: Optional[Dict] = None) -> List[str]:
        """
        Determine model capabilities from its ID and configuration.
        
        Args:
            model_id: Model ID
            model_config: Model configuration, if available
            
        Returns:
            List of capabilities
        """
        capabilities = []
        model_id_lower = model_id.lower()
        
        # Check model name for hints
        if any(kw in model_id_lower for kw in ["vit", "vision", "clip", "blip", "image"]):
            capabilities.append("image")
        
        if any(kw in model_id_lower for kw in ["video", "videomae", "movinet"]):
            capabilities.append("video")
        
        if any(kw in model_id_lower for kw in ["llava", "blip", "instruct", "qwen-vl"]):
            capabilities.extend(["image", "text"])
        
        # Add text capability by default
        if not capabilities or any(kw in model_id_lower for kw in [
            "bert", "gpt", "t5", "llama", "mistral", "phi", "qwen"
        ]):
            capabilities.append("text")
        
        # Check model config if available
        if model_config:
            arch_type = model_config.get("architectures", [""])[0].lower()
            model_type = model_config.get("model_type", "").lower()
            
            # Vision models
            if any(kw in arch_type or kw in model_type for kw in [
                "vit", "clip", "blip", "sam", "yolo", "detr", "swin"
            ]):
                if "image" not in capabilities:
                    capabilities.append("image")
            
            # Video models
            if any(kw in arch_type or kw in model_type for kw in [
                "videomae", "movinet", "timesformer"
            ]):
                if "video" not in capabilities:
                    capabilities.append("video")
        
        return capabilities
    
    def _extract_tags_from_model(self, model_id: str, model_info: Optional[Dict] = None) -> List[str]:
        """
        Extract tags from model ID and info.
        
        Args:
            model_id: Model ID
            model_info: Model info from API, if available
            
        Returns:
            List of tags
        """
        tags = []
        model_id_lower = model_id.lower()
        
        # Extract size indicators
        if any(kw in model_id_lower for kw in ["tiny", "small", "mini", "lite"]):
            tags.append("small")
        elif any(kw in model_id_lower for kw in ["medium", "base"]):
            tags.append("medium")
        elif any(kw in model_id_lower for kw in ["large", "xl", "huge"]):
            tags.append("large")
        
        # Extract model capabilities
        if any(kw in model_id_lower for kw in ["vision", "vit", "clip", "blip", "image"]):
            tags.append("vision")
        
        if any(kw in model_id_lower for kw in ["video"]):
            tags.append("video")
        
        if "instruct" in model_id_lower:
            tags.append("instruct")
        
        if any(kw in model_id_lower for kw in ["multimodal", "llava", "blip", "qwen-vl"]):
            tags.append("multimodal")
        
        # Extract model type
        for model_type in ["bert", "gpt", "t5", "llama", "mistral", "phi", "qwen", "clip", "blip"]:
            if model_type in model_id_lower:
                tags.append(model_type)
        
        # Add tags from model info
        if model_info and "tags" in model_info:
            tags.extend(model_info["tags"])
        
        return list(set(tags))  # Remove duplicates
    
    def _get_model_size(self, model_id: str, local_path: Optional[str] = None) -> int:
        """
        Estimate model size in MB.
        
        Args:
            model_id: Model ID
            local_path: Path to local files, if available
            
        Returns:
            Size in MB
        """
        # If local path is available, use it to calculate size
        if local_path and os.path.exists(local_path):
            total_size = 0
            for root, _, files in os.walk(local_path):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            return int(total_size / (1024 * 1024))
        
        # Otherwise, use model ID to estimate size
        model_id_lower = model_id.lower()
        
        # Estimate based on model name
        if any(kw in model_id_lower for kw in ["tiny", "mini", "small", "lite"]):
            return 300
        elif any(kw in model_id_lower for kw in ["medium", "base"]):
            return 500
        elif "large" in model_id_lower:
            return 1500
        elif "xl" in model_id_lower:
            return 3000
        elif "xxl" in model_id_lower:
            return 6000
        
        # Default size
        return 500
    
    def _refresh_models_cache(self, force: bool = False) -> None:
        """
        Refresh the models cache.
        
        Args:
            force: Force refresh even if cache is still valid
        """
        current_time = time.time()
        if force or (current_time - self._last_refresh) > self._cache_ttl:
            logger.debug("Refreshing models cache")
            
            # Get locally cached models
            self._scan_local_cache()
            
            # In online mode, also get models from Hub
            if not self.offline_mode:
                try:
                    # This is expensive, so we only do it on force refresh
                    if force:
                        self._fetch_recommended_models()
                except Exception as e:
                    logger.error(f"Error fetching models from Hugging Face Hub: {e}")
            
            self._last_refresh = current_time
    
    def _scan_local_cache(self) -> None:
        """Scan local Hugging Face cache for models."""
        try:
            local_models = scan_cache_dir()
            
            for repo in local_models.repos:
                for revision in repo.revisions:
                    model_id = repo.repo_id
                    
                    # Skip datasets and non-model repositories
                    if model_id.startswith("datasets/"):
                        continue
                    
                    # Create or update model info
                    if model_id not in self._models_cache:
                        local_path = revision.snapshot_path
                        
                        # Try to load config to determine capabilities
                        capabilities = []
                        try:
                            config_path = os.path.join(local_path, "config.json")
                            if os.path.exists(config_path):
                                with open(config_path, "r") as f:
                                    config = json.load(f)
                                capabilities = self._get_model_capabilities(model_id, config)
                        except Exception as e:
                            logger.debug(f"Error loading model config: {e}")
                            capabilities = self._get_model_capabilities(model_id)
                        
                        # Create model info
                        self._models_cache[model_id] = ModelInfo(
                            name=model_id,
                            provider="huggingface",
                            size_mb=self._get_model_size(model_id, local_path),
                            tags=self._extract_tags_from_model(model_id),
                            version=revision.commit_hash[:7],
                            capabilities=capabilities,
                            loaded=model_id in self._loaded_models,
                            metadata={"local_path": local_path}
                        )
        except Exception as e:
            logger.error(f"Error scanning local cache: {e}")
    
    def _fetch_recommended_models(self) -> None:
        """Fetch recommended models from Hugging Face Hub."""
        try:
            # Common multimodal models
            multimodal_models = ["llava-hf/llava-1.5-7b-hf", "Salesforce/blip2-opt-2.7b", 
                               "microsoft/phi-3-vision-128k", "Qwen/Qwen-VL"]
                               
            # Process recommended models
            for model_id in multimodal_models:
                if model_id not in self._models_cache:
                    try:
                        # Get model info from Hub
                        model_info = self.api.model_info(model_id)
                        
                        # Create model info
                        self._models_cache[model_id] = ModelInfo(
                            name=model_id,
                            provider="huggingface",
                            size_mb=self._get_model_size(model_id),
                            tags=self._extract_tags_from_model(model_id, model_info),
                            version="latest",
                            capabilities=self._get_model_capabilities(model_id),
                            loaded=model_id in self._loaded_models,
                            metadata={"remote_only": True}
                        )
                    except Exception as e:
                        logger.debug(f"Error fetching info for model {model_id}: {e}")
            
            # Special handling for multimodal models
            # Query for multimodal vision-language models with filter
            if not self.offline_mode and self.auth_token:
                multimodal_filter = ModelFilter(
                    task="multimodal",
                    library="transformers",
                    model_name="llava|blip|instruct-vlm|phi-3-vision"
                )
                
                for model in list_models(filter=multimodal_filter, limit=20):
                    model_id = model.id
                    if model_id not in self._models_cache:
                        self._models_cache[model_id] = ModelInfo(
                            name=model_id,
                            provider="huggingface",
                            size_mb=self._get_model_size(model_id),
                            tags=self._extract_tags_from_model(model_id),
                            version="latest",
                            capabilities=["image", "text"],
                            loaded=model_id in self._loaded_models,
                            metadata={"remote_only": True}
                        )
        except Exception as e:
            logger.error(f"Error fetching recommended models: {e}")
    
    def list_available_models(self) -> List[ModelInfo]:
        """
        List all available models from Hugging Face.
        This includes both installed models and recommended models.
        
        Returns:
            List of ModelInfo objects
        """
        # Refresh cache if needed
        self._refresh_models_cache()
        
        # Return all models in cache
        return list(self._models_cache.values())
    
    def list_installed_models(self) -> List[ModelInfo]:
        """
        List all installed models.
        
        Returns:
            List of ModelInfo objects
        """
        # Refresh cache if needed
        self._refresh_models_cache()
        
        # Return only locally installed models
        return [
            model for model in self._models_cache.values()
            if not model.metadata.get("remote_only", False)
        ]
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo object or None if not found
        """
        # Refresh cache if needed
        self._refresh_models_cache()
        
        # Find exact match
        if model_name in self._models_cache:
            return self._models_cache[model_name]
        
        # Try case-insensitive match
        model_name_lower = model_name.lower()
        for name, model in self._models_cache.items():
            if name.lower() == model_name_lower:
                return model
        
        # If in online mode and not found, try to fetch from Hub
        if not self.offline_mode:
            try:
                model_info = self.api.model_info(model_name)
                
                # Create model info
                model = ModelInfo(
                    name=model_name,
                    provider="huggingface",
                    size_mb=self._get_model_size(model_name),
                    tags=self._extract_tags_from_model(model_name, model_info),
                    version="latest",
                    capabilities=self._get_model_capabilities(model_name),
                    loaded=model_name in self._loaded_models,
                    metadata={"remote_only": True}
                )
                
                # Add to cache
                self._models_cache[model_name] = model
                
                return model
            except Exception as e:
                logger.debug(f"Error fetching info for model {model_name}: {e}")
        
        return None
    
    def download_model(self, model_name: str) -> bool:
        """
        Download a model from Hugging Face.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if self.offline_mode:
            logger.error("Cannot download models in offline mode")
            return False
        
        logger.info(f"Downloading Hugging Face model: {model_name}")
        
        try:
            # Use transformers library to download model files
            AutoModel.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                use_auth_token=self.auth_token,
                local_files_only=False,
                force_download=True,
                resume_download=True,
            )
            
            # Also download tokenizer
            try:
                AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.cache_dir,
                    use_auth_token=self.auth_token,
                    local_files_only=False,
                )
            except Exception as e:
                logger.warning(f"Error downloading tokenizer for {model_name}: {e}")
            
            # Force refresh cache
            self._refresh_models_cache(force=True)
            
            return True
        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            return False
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if model_name in self._loaded_models:
            logger.info(f"Model {model_name} already loaded")
            return True
        
        if not self.is_model_available(model_name) and not self.offline_mode:
            logger.info(f"Model {model_name} not available locally, downloading")
            if not self.download_model(model_name):
                logger.error(f"Failed to download model {model_name}")
                return False
        
        logger.info(f"Loading Hugging Face model: {model_name}")
        
        try:
            # Try to determine the appropriate pipeline
            model_info = self.get_model_info(model_name)
            if not model_info:
                logger.error(f"Model {model_name} not found")
                return False
            
            # Determine pipeline type based on capabilities
            pipeline_type = "text-generation"  # Default
            if "image" in model_info.capabilities and "text" in model_info.capabilities:
                # This is a multimodal model
                self._loaded_models[model_name] = {
                    "model": AutoModel.from_pretrained(
                        model_name,
                        cache_dir=self.cache_dir,
                        use_auth_token=self.auth_token,
                        local_files_only=self.offline_mode,
                        device_map=self.device
                    ),
                    "tokenizer": AutoTokenizer.from_pretrained(
                        model_name,
                        cache_dir=self.cache_dir,
                        use_auth_token=self.auth_token,
                        local_files_only=self.offline_mode,
                    ),
                    "pipeline": None,  # No standard pipeline for multimodal yet
                    "type": "multimodal"
                }
            elif "image" in model_info.capabilities:
                pipeline_type = "image-classification"
                self._loaded_models[model_name] = {
                    "pipeline": pipeline(
                        pipeline_type,
                        model=model_name,
                        device=self.device
                    ),
                    "type": "vision"
                }
            else:
                # Text model
                self._loaded_models[model_name] = {
                    "pipeline": pipeline(
                        pipeline_type,
                        model=model_name,
                        device=self.device
                    ),
                    "type": "text"
                }
            
            # Update model info in cache
            if model_name in self._models_cache:
                self._models_cache[model_name].loaded = True
            
            return True
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if successful, False otherwise
        """
        if model_name not in self._loaded_models:
            logger.info(f"Model {model_name} not loaded")
            return True
        
        logger.info(f"Unloading Hugging Face model: {model_name}")
        
        try:
            # Get model container
            model_container = self._loaded_models[model_name]
            
            # Unload based on type
            if "pipeline" in model_container:
                del model_container["pipeline"]
            
            if "model" in model_container:
                del model_container["model"]
            
            if "tokenizer" in model_container:
                del model_container["tokenizer"]
            
            # Remove from loaded models
            del self._loaded_models[model_name]
            
            # Update model info in cache
            if model_name in self._models_cache:
                self._models_cache[model_name].loaded = False
            
            # Force garbage collection to free memory
            import gc
            gc.collect()
            
            # Clear CUDA cache if applicable
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return True
        except Exception as e:
            logger.error(f"Error unloading model {model_name}: {e}")
            return False
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available locally.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if available, False otherwise
        """
        model_info = self.get_model_info(model_name)
        if not model_info:
            return False
        
        return not model_info.metadata.get("remote_only", False)
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is loaded in memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if loaded, False otherwise
        """
        return model_name in self._loaded_models
    
    def get_loaded_model(self, model_name: str) -> Optional[Any]:
        """
        Get a loaded model for direct use.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Loaded model or None if not loaded
        """
        if not self.is_model_loaded(model_name):
            logger.error(f"Model {model_name} not loaded")
            return None
        
        return self._loaded_models[model_name]
