#!/usr/bin/env python3
"""
Configuration System for Multimodal Processing

This module provides a configuration system for the multimodal processing components.
It includes default configurations, environment variable support, and file-based config.

The configuration system is used to manage:
1. Model paths and preferences
2. Hardware adaptation settings
3. Processing parameters
4. Fallback options
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict

# Configure logging
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_FILE = "multimodal_config.json"
DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".techsaas")

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str = "ollama"  # "ollama" or "huggingface"
    tags: List[str] = field(default_factory=list)
    min_ram_gb: float = 8.0
    min_gpu_gb: float = 0.0
    requires_gpu: bool = False
    fallback_model: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    path: Optional[str] = None
    
    def is_huggingface(self) -> bool:
        """Check if the model is from HuggingFace."""
        return self.provider.lower() == "huggingface"
    
    def is_ollama(self) -> bool:
        """Check if the model is from Ollama."""
        return self.provider.lower() == "ollama"


@dataclass
class ProcessingConfig:
    """Configuration for multimodal processing."""
    batch_size: int = 4
    max_frames: int = 30
    frame_interval: int = 10  # Extract every Nth frame
    image_size: int = 512  # Image resolution for processing
    cache_results: bool = True
    cache_dir: Optional[str] = None


@dataclass
class MultimodalConfig:
    """Complete configuration for multimodal processing."""
    # Hardware adaptation
    adapt_to_hardware: bool = True
    gpu_preferred: bool = True
    memory_buffer_gb: float = 2.0  # Keep this much RAM free
    
    # Models configuration
    default_image_model: str = "llava:latest"
    default_video_model: str = "llava:latest"
    default_text_model: str = "phi3:mini"
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    
    # Processing configuration
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    # Paths and directories
    model_cache_dir: Optional[str] = None
    result_cache_dir: Optional[str] = None
    
    # Advanced options
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = asdict(self)
        return config_dict
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MultimodalConfig':
        """Create configuration from dictionary."""
        # Extract the models dictionary
        models_dict = config_dict.pop("models", {})
        
        # Convert model dictionaries to ModelConfig objects
        models = {}
        for name, model_dict in models_dict.items():
            models[name] = ModelConfig(**model_dict)
        
        # Extract processing configuration
        processing_dict = config_dict.pop("processing", {})
        processing = ProcessingConfig(**processing_dict)
        
        # Create main configuration
        config = cls(**config_dict)
        config.models = models
        config.processing = processing
        
        return config


def create_default_config() -> MultimodalConfig:
    """
    Create a default configuration with sensible values.
    
    Returns:
        MultimodalConfig: Default configuration
    """
    # Create cache directories
    home_dir = os.path.expanduser("~")
    cache_dir = os.path.join(home_dir, ".techsaas", "cache")
    model_cache_dir = os.path.join(cache_dir, "models")
    result_cache_dir = os.path.join(cache_dir, "results")
    
    # Ensure directories exist
    os.makedirs(model_cache_dir, exist_ok=True)
    os.makedirs(result_cache_dir, exist_ok=True)
    
    # Create default model configurations
    models = {
        "llava:latest": ModelConfig(
            name="llava:latest",
            provider="ollama",
            tags=["image", "video", "multimodal"],
            min_ram_gb=16.0,
            min_gpu_gb=8.0,
            requires_gpu=True,
            fallback_model="phi-3.5-vision:latest",
            parameters={"temperature": 0.7, "max_length": 1024}
        ),
        "phi-3.5-vision:latest": ModelConfig(
            name="phi-3.5-vision:latest",
            provider="huggingface",
            tags=["image", "video", "multimodal", "efficient"],
            min_ram_gb=8.0,
            min_gpu_gb=0.0,
            requires_gpu=False,
            fallback_model="phi-lite:latest",
            parameters={"temperature": 0.7, "max_length": 512}
        ),
        "phi-lite:latest": ModelConfig(
            name="phi-lite:latest",
            provider="huggingface",
            tags=["image", "video", "multimodal", "efficient", "lite"],
            min_ram_gb=4.0,
            min_gpu_gb=0.0,
            requires_gpu=False,
            fallback_model=None,
            parameters={"temperature": 0.7, "max_length": 256}
        ),
        "phi3:mini": ModelConfig(
            name="phi3:mini",
            provider="ollama",
            tags=["text", "efficient"],
            min_ram_gb=4.0,
            min_gpu_gb=0.0,
            requires_gpu=False,
            parameters={"temperature": 0.7, "max_length": 512}
        )
    }
    
    # Create processing configuration
    processing = ProcessingConfig(
        batch_size=4,
        max_frames=30,
        frame_interval=10,
        image_size=512,
        cache_results=True,
        cache_dir=result_cache_dir
    )
    
    # Create and return default configuration
    return MultimodalConfig(
        adapt_to_hardware=True,
        gpu_preferred=True,
        memory_buffer_gb=2.0,
        default_image_model="llava:latest",
        default_video_model="llava:latest",
        default_text_model="phi3:mini",
        models=models,
        processing=processing,
        model_cache_dir=model_cache_dir,
        result_cache_dir=result_cache_dir,
        debug_mode=False,
        log_level="INFO"
    )


def load_config(config_file: Optional[str] = None) -> MultimodalConfig:
    """
    Load configuration from file.
    
    Args:
        config_file: Path to configuration file (defaults to ~/.techsaas/multimodal_config.json)
        
    Returns:
        MultimodalConfig: Loaded configuration (or default if file not found)
    """
    if config_file is None:
        config_dir = os.environ.get("TECHSAAS_CONFIG_DIR", DEFAULT_CONFIG_DIR)
        config_file = os.path.join(config_dir, DEFAULT_CONFIG_FILE)
    
    # If config file doesn't exist, create default config
    if not os.path.exists(config_file):
        logger.info(f"Configuration file not found: {config_file}")
        config = create_default_config()
        
        # Try to save the default config
        try:
            save_config(config, config_file)
        except Exception as e:
            logger.warning(f"Could not save default configuration: {e}")
        
        return config
    
    # Load configuration from file
    try:
        with open(config_file, "r") as f:
            config_dict = json.load(f)
        
        logger.info(f"Loaded configuration from {config_file}")
        return MultimodalConfig.from_dict(config_dict)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        logger.info("Using default configuration")
        return create_default_config()


def save_config(config: MultimodalConfig, config_file: Optional[str] = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_file: Path to configuration file (defaults to ~/.techsaas/multimodal_config.json)
    """
    if config_file is None:
        config_dir = os.environ.get("TECHSAAS_CONFIG_DIR", DEFAULT_CONFIG_DIR)
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, DEFAULT_CONFIG_FILE)
    
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
    
    # Save configuration to file
    try:
        with open(config_file, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        
        logger.info(f"Saved configuration to {config_file}")
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")


# Global configuration instance
_config = None

def get_config(reload: bool = False) -> MultimodalConfig:
    """
    Get the current configuration, using a cached version if available.
    
    Args:
        reload: If True, reload configuration from file
        
    Returns:
        MultimodalConfig: Current configuration
    """
    global _config
    
    if _config is None or reload:
        _config = load_config()
    
    return _config


if __name__ == "__main__":
    # Set up logging for command-line usage
    logging.basicConfig(level=logging.INFO)
    
    # Create and print default configuration
    config = create_default_config()
    print(json.dumps(config.to_dict(), indent=2))
    
    # Example of saving configuration
    config_file = os.path.join(os.getcwd(), "multimodal_config.json")
    save_config(config, config_file)
    print(f"Saved default configuration to {config_file}")
