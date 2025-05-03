#!/usr/bin/env python3
"""
Hardware Detection Utility for Multimodal Processing

This module provides functions to detect and evaluate available hardware
capabilities, allowing the multimodal processing system to make intelligent
decisions about which models to use based on:
- GPU availability and capabilities
- Available memory
- CPU capabilities
- Disk space

The hardware profile is used to:
1. Select appropriate models (e.g., full-size vs. quantized)
2. Determine batch sizes for processing
3. Enable/disable features based on hardware constraints
4. Provide fallback options when hardware is insufficient
"""

import os
import sys
import platform
import logging
import subprocess
import shutil
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

# Constants for minimum requirements
MIN_RAM_GB = 4.0
MIN_DISK_GB = 5.0
RECOMMENDED_RAM_GB = {
    "low": 8.0,
    "medium": 16.0,
    "high": 32.0
}

@dataclass
class GPUInfo:
    """Information about an available GPU."""
    name: str
    memory_gb: float
    cuda_capability: Optional[str] = None
    is_available: bool = True
    
    def __str__(self) -> str:
        return f"{self.name} ({self.memory_gb:.1f}GB)"

@dataclass
class HardwareProfile:
    """Complete hardware profile for the system."""
    has_gpu: bool = False
    gpus: List[GPUInfo] = None
    cpu_count: int = 0
    total_ram_gb: float = 0.0
    available_ram_gb: float = 0.0
    total_disk_gb: float = 0.0
    available_disk_gb: float = 0.0
    platform: str = ""
    cuda_available: bool = False
    mps_available: bool = False  # Metal Performance Shaders (Apple Silicon)
    directml_available: bool = False  # DirectML (Windows)
    
    def __post_init__(self):
        if self.gpus is None:
            self.gpus = []
        self.has_gpu = len(self.gpus) > 0
    
    def get_capability_level(self) -> str:
        """
        Determine the overall capability level of the hardware.
        
        Returns:
            str: One of "low", "medium", "high" based on available hardware
        """
        # Default to low capabilities
        level = "low"
        
        # Check for GPU with sufficient memory
        if self.has_gpu and any(gpu.memory_gb >= 8.0 for gpu in self.gpus):
            level = "high"
        elif self.has_gpu and any(gpu.memory_gb >= 4.0 for gpu in self.gpus):
            level = "medium"
        # CPU-only with sufficient RAM
        elif self.available_ram_gb >= RECOMMENDED_RAM_GB["medium"]:
            level = "medium"
        
        # Downgrade if available disk space is too low
        if self.available_disk_gb < MIN_DISK_GB:
            level = "low"
        
        return level
    
    def can_run_model(self, model_requirements: Dict[str, Any]) -> bool:
        """
        Check if the hardware can run a specific model.
        
        Args:
            model_requirements: Dictionary with minimum hardware requirements
                keys: min_ram_gb, min_gpu_gb, min_disk_gb, etc.
                
        Returns:
            bool: True if the hardware meets the requirements
        """
        # Check minimum RAM
        if model_requirements.get("min_ram_gb", 0) > self.available_ram_gb:
            return False
        
        # Check GPU if required
        if model_requirements.get("requires_gpu", False) and not self.has_gpu:
            return False
        
        # Check GPU memory if specified
        min_gpu_memory = model_requirements.get("min_gpu_gb", 0)
        if min_gpu_memory > 0 and not any(gpu.memory_gb >= min_gpu_memory for gpu in self.gpus):
            return False
        
        # Check available disk space
        if model_requirements.get("min_disk_gb", 0) > self.available_disk_gb:
            return False
        
        return True
    
    def get_recommended_batch_size(self, model_name: str) -> int:
        """
        Get recommended batch size for a given model based on hardware.
        
        Args:
            model_name: Name of the model
            
        Returns:
            int: Recommended batch size (default: 1)
        """
        # Simple heuristics based on capability level
        level = self.get_capability_level()
        
        if level == "high":
            return 16
        elif level == "medium":
            return 8
        else:
            return 4
    
    def __str__(self) -> str:
        """String representation of the hardware profile."""
        gpu_str = "None" if not self.has_gpu else ", ".join(str(gpu) for gpu in self.gpus)
        return (
            f"Platform: {self.platform}\n"
            f"CPU Count: {self.cpu_count}\n"
            f"RAM: {self.available_ram_gb:.1f}GB / {self.total_ram_gb:.1f}GB\n"
            f"Disk Space: {self.available_disk_gb:.1f}GB / {self.total_disk_gb:.1f}GB\n"
            f"GPUs: {gpu_str}\n"
            f"CUDA Available: {self.cuda_available}\n"
            f"MPS Available: {self.mps_available}\n"
            f"DirectML Available: {self.directml_available}\n"
            f"Capability Level: {self.get_capability_level()}"
        )


def get_platform_info() -> str:
    """
    Get detailed platform information.
    
    Returns:
        str: Platform information string
    """
    system = platform.system()
    if system == "Linux":
        # Check for specific Linux distribution
        try:
            import distro
            return f"{distro.name()} {distro.version()}"
        except ImportError:
            try:
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip().strip('"')
            except:
                pass
    
    return f"{platform.system()} {platform.release()}"


def get_cpu_info() -> int:
    """
    Get CPU information.
    
    Returns:
        int: Number of CPU cores/threads
    """
    import multiprocessing
    return multiprocessing.cpu_count()


def get_memory_info() -> Tuple[float, float]:
    """
    Get system memory (RAM) information.
    
    Returns:
        tuple: (total_ram_gb, available_ram_gb)
    """
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_ram_gb = vm.total / (1024 ** 3)
        available_ram_gb = vm.available / (1024 ** 3)
        return total_ram_gb, available_ram_gb
    except ImportError:
        logger.warning("psutil not installed, using fallback for memory detection")
        # Fallback to estimate based on platform
        if platform.system() == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    mem_info = f.read()
                    total_kb = int(mem_info.split("MemTotal:")[1].split("kB")[0].strip())
                    available_kb = int(mem_info.split("MemAvailable:")[1].split("kB")[0].strip())
                    return total_kb / (1024 ** 2), available_kb / (1024 ** 2)
            except:
                pass
        
        # If all else fails, use a conservative estimate
        return 8.0, 4.0


def get_disk_info(path: str = None) -> Tuple[float, float]:
    """
    Get disk space information.
    
    Args:
        path: Path to check disk space (defaults to current directory)
        
    Returns:
        tuple: (total_disk_gb, available_disk_gb)
    """
    if path is None:
        path = os.getcwd()
    
    try:
        total, used, free = shutil.disk_usage(path)
        return total / (1024 ** 3), free / (1024 ** 3)
    except:
        logger.warning(f"Could not get disk usage for {path}")
        return 50.0, 10.0  # Conservative default


def check_cuda_available() -> bool:
    """
    Check if CUDA is available.
    
    Returns:
        bool: True if CUDA is available
    """
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        logger.debug("PyTorch not installed, checking for CUDA with subprocess")
        try:
            result = subprocess.run(
                ["nvidia-smi"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=3
            )
            return result.returncode == 0
        except:
            return False


def check_mps_available() -> bool:
    """
    Check if MPS (Metal Performance Shaders) is available (Apple Silicon).
    
    Returns:
        bool: True if MPS is available
    """
    if platform.system() != "Darwin":  # macOS only
        return False
    
    try:
        import torch
        return torch.backends.mps.is_available()
    except (ImportError, AttributeError):
        return False


def check_directml_available() -> bool:
    """
    Check if DirectML is available (Windows).
    
    Returns:
        bool: True if DirectML is available
    """
    if platform.system() != "Windows":
        return False
    
    try:
        import torch_directml
        return True
    except ImportError:
        return False


def get_gpu_info() -> List[GPUInfo]:
    """
    Get information about available GPUs.
    
    Returns:
        list: List of GPUInfo objects
    """
    gpus = []
    
    # Check for NVIDIA GPUs using PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                try:
                    props = torch.cuda.get_device_properties(i)
                    gpus.append(GPUInfo(
                        name=props.name,
                        memory_gb=props.total_memory / (1024 ** 3),
                        cuda_capability=f"{props.major}.{props.minor}"
                    ))
                except:
                    logger.warning(f"Could not get properties for CUDA device {i}")
    except ImportError:
        logger.debug("PyTorch not installed, checking for GPUs with subprocess")
    
    # Fallback to nvidia-smi if PyTorch isn't available
    if not gpus:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(",")
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        memory_mb = float(parts[1].strip())
                        gpus.append(GPUInfo(
                            name=name,
                            memory_gb=memory_mb / 1024
                        ))
        except:
            logger.debug("Could not get GPU information from nvidia-smi")
    
    # Check for Apple Silicon GPU
    if platform.system() == "Darwin" and platform.processor() == "arm":
        try:
            # Rough approximation - Apple Silicon shares RAM with GPU
            total_ram_gb, _ = get_memory_info()
            gpu_memory_gb = total_ram_gb / 2  # Estimate GPU memory as half of total RAM
            
            gpus.append(GPUInfo(
                name="Apple Silicon",
                memory_gb=gpu_memory_gb,
                is_available=check_mps_available()
            ))
        except:
            logger.debug("Could not determine Apple Silicon GPU info")
    
    return gpus


def get_hardware_profile() -> HardwareProfile:
    """
    Get complete hardware profile for the system.
    
    Returns:
        HardwareProfile: Complete hardware profile
    """
    logger.info("Detecting hardware capabilities...")
    
    # Get platform information
    platform_info = get_platform_info()
    
    # Get CPU information
    cpu_count = get_cpu_info()
    
    # Get memory information
    total_ram_gb, available_ram_gb = get_memory_info()
    
    # Get disk information
    total_disk_gb, available_disk_gb = get_disk_info()
    
    # Get GPU information
    gpus = get_gpu_info()
    has_gpu = len(gpus) > 0
    
    # Check for accelerator availability
    cuda_available = check_cuda_available()
    mps_available = check_mps_available()
    directml_available = check_directml_available()
    
    # Create hardware profile
    profile = HardwareProfile(
        has_gpu=has_gpu,
        gpus=gpus,
        cpu_count=cpu_count,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        total_disk_gb=total_disk_gb,
        available_disk_gb=available_disk_gb,
        platform=platform_info,
        cuda_available=cuda_available,
        mps_available=mps_available,
        directml_available=directml_available
    )
    
    logger.info(f"Hardware profile detected: {profile.get_capability_level()} capability")
    logger.debug(str(profile))
    
    return profile


# Cache for hardware profile to avoid repeated detection
_hardware_profile = None

def get_current_hardware_profile(force_refresh: bool = False) -> HardwareProfile:
    """
    Get the current hardware profile, using a cached version if available.
    
    Args:
        force_refresh: If True, regenerate the hardware profile
        
    Returns:
        HardwareProfile: Current hardware profile
    """
    global _hardware_profile
    
    if _hardware_profile is None or force_refresh:
        _hardware_profile = get_hardware_profile()
    
    return _hardware_profile


if __name__ == "__main__":
    # Set up logging for command-line usage
    logging.basicConfig(level=logging.INFO)
    
    # Detect and print hardware profile
    profile = get_hardware_profile()
    print("\nHardware Profile:")
    print("================")
    print(profile)
    print("\nCapability Level:", profile.get_capability_level())
    
    # Example model requirements
    llava_model = {
        "name": "llava:latest",
        "min_ram_gb": 8.0,
        "min_gpu_gb": 8.0,
        "requires_gpu": True
    }
    
    phi_model = {
        "name": "phi-3.5-vision:latest", 
        "min_ram_gb": 8.0,
        "min_gpu_gb": 0.0,
        "requires_gpu": False
    }
    
    # Check if models can run
    print("\nModel Compatibility:")
    print("===================")
    print(f"Can run {llava_model['name']}: {profile.can_run_model(llava_model)}")
    print(f"Can run {phi_model['name']}: {profile.can_run_model(phi_model)}")
    
    # Show batch size recommendations
    print("\nRecommended Batch Sizes:")
    print("======================")
    print(f"Batch size for {llava_model['name']}: {profile.get_recommended_batch_size(llava_model['name'])}")
    print(f"Batch size for {phi_model['name']}: {profile.get_recommended_batch_size(phi_model['name'])}")
