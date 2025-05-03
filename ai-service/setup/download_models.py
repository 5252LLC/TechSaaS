#!/usr/bin/env python3
"""
Model Download and Management Script

This script handles the downloading and management of AI models for the
LangChain and Ollama integration. It supports:
- Downloading specified models via Ollama
- Verifying model integrity
- Caching models to avoid redundant downloads
- Resuming interrupted downloads

The script is designed to work with the Ollama API and CLI to manage models.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('model-manager')

# Default models to download
DEFAULT_MODELS = [
    "llama3.2:3b",    # Llama 3.2 3B parameters model
    "mistral:latest"  # Mistral model (backup option if other models aren't available)
]

# Ollama API endpoint
OLLAMA_API_ENDPOINT = "http://localhost:11434/api"

# Ollama model directory (platform-specific)
OLLAMA_MODEL_DIRS = {
    "linux": "~/.ollama/models",
    "darwin": "~/.ollama/models",
    "windows": "~/.ollama/models"  # For Windows under WSL
}


def get_platform() -> str:
    """
    Detect the current platform.
    
    Returns:
        str: Platform string (linux, darwin, or windows)
    """
    import platform
    system = platform.system().lower()
    
    if system in ("linux", "darwin", "windows"):
        return system
    
    # Default to linux if unknown
    logger.warning(f"Unknown platform: {system}. Defaulting to linux.")
    return "linux"


def get_model_dir() -> Path:
    """
    Get the Ollama model directory for the current platform.
    
    Returns:
        Path: Path to the Ollama model directory
    """
    platform = get_platform()
    model_dir = os.path.expanduser(OLLAMA_MODEL_DIRS.get(platform, OLLAMA_MODEL_DIRS["linux"]))
    return Path(model_dir)


def is_ollama_running() -> bool:
    """
    Check if Ollama server is running.
    
    Returns:
        bool: True if Ollama is running, False otherwise
    """
    try:
        # Try to connect to the Ollama API
        import urllib.request
        import urllib.error
        
        try:
            with urllib.request.urlopen(f"{OLLAMA_API_ENDPOINT}/tags", timeout=2) as response:
                return response.status == 200
        except urllib.error.URLError:
            pass
        
        # Alternative: check if the process is running
        if get_platform() == "windows":
            # For Windows
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq ollama.exe"],
                capture_output=True,
                text=True,
                check=False
            )
            return "ollama.exe" in result.stdout
        else:
            # For Linux/macOS
            result = subprocess.run(
                ["pgrep", "-f", "ollama serve"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip() != ""
    
    except Exception as e:
        logger.debug(f"Error checking if Ollama is running: {str(e)}")
        return False


def start_ollama() -> bool:
    """
    Start the Ollama server if it's not already running.
    
    Returns:
        bool: True if Ollama started successfully or was already running
    """
    if is_ollama_running():
        logger.info("Ollama is already running")
        return True
    
    logger.info("Starting Ollama server")
    try:
        # Start Ollama in the background
        if get_platform() == "windows":
            # For Windows
            process = subprocess.Popen(
                ["start", "/B", "ollama", "serve"],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            # For Linux/macOS
            process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        # Wait for Ollama to start (up to 10 seconds)
        for _ in range(10):
            time.sleep(1)
            if is_ollama_running():
                logger.info("Ollama server started successfully")
                return True
        
        # If we get here, Ollama didn't start
        logger.error("Failed to start Ollama server")
        return False
    
    except Exception as e:
        logger.error(f"Error starting Ollama: {str(e)}")
        return False


def stop_ollama() -> bool:
    """
    Stop the Ollama server if it was started by this script.
    
    Returns:
        bool: True if Ollama stopped successfully
    """
    if not is_ollama_running():
        logger.info("Ollama is not running")
        return True
    
    logger.info("Stopping Ollama server")
    try:
        if get_platform() == "windows":
            # For Windows
            subprocess.run(
                ["taskkill", "/F", "/IM", "ollama.exe"],
                capture_output=True,
                check=False
            )
        else:
            # For Linux/macOS
            subprocess.run(
                ["pkill", "-f", "ollama serve"],
                capture_output=True,
                check=False
            )
        
        # Wait for Ollama to stop (up to 5 seconds)
        for _ in range(5):
            time.sleep(1)
            if not is_ollama_running():
                logger.info("Ollama server stopped successfully")
                return True
        
        # If we get here, Ollama didn't stop
        logger.error("Failed to stop Ollama server")
        return False
    
    except Exception as e:
        logger.error(f"Error stopping Ollama: {str(e)}")
        return False


def list_available_models() -> List[str]:
    """
    List models that are available in the Ollama registry.
    
    Returns:
        List[str]: List of available model names
    """
    logger.info("Retrieving available models from Ollama registry")
    
    try:
        # Use Ollama CLI to list available models
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract model names from output
        models = []
        for line in result.stdout.strip().split('\n')[1:]:  # Skip header
            if line.strip():
                # Format: NAME TAG SIZE MODIFIED
                parts = re.split(r'\s+', line.strip(), maxsplit=3)
                if len(parts) >= 2:
                    model_name = f"{parts[0]}:{parts[1]}"
                    # Remove hash suffix if present (format: name:tag:hash)
                    if ":" in model_name:
                        base_model = model_name.split(":", 2)[0:2]
                        models.append(":".join(base_model))
                    else:
                        models.append(model_name)
        
        return models
    
    except Exception as e:
        logger.error(f"Error listing available models: {str(e)}")
        return []


def list_installed_models() -> List[str]:
    """
    List models that are already installed on the local system.
    
    Returns:
        List[str]: List of installed model names
    """
    try:
        # Get installed models using Ollama API
        if is_ollama_running():
            try:
                import urllib.request
                import json
                
                with urllib.request.urlopen(f"{OLLAMA_API_ENDPOINT}/tags") as response:
                    data = json.loads(response.read().decode('utf-8'))
                    models = []
                    for model in data.get('models', []):
                        # Format as name:tag without hash
                        model_name = f"{model['name']}:{model['tag']}"
                        models.append(model_name)
                    return models
            except Exception as e:
                logger.debug(f"Error using API to list models: {str(e)}")
                # Fall back to CLI method
        
        # Fall back to using Ollama CLI
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract model names from output
        models = []
        for line in result.stdout.strip().split('\n')[1:]:  # Skip header
            if line.strip():
                # Format: NAME TAG SIZE MODIFIED
                parts = re.split(r'\s+', line.strip(), maxsplit=3)
                if len(parts) >= 2:
                    model_name = f"{parts[0]}:{parts[1]}"
                    # Remove hash suffix if present
                    if ":" in model_name:
                        base_model = model_name.split(":", 2)[0:2]
                        models.append(":".join(base_model))
                    else:
                        models.append(model_name)
        
        return models
    
    except Exception as e:
        logger.error(f"Error listing installed models: {str(e)}")
        return []


def normalize_model_name(model_name: str) -> str:
    """
    Normalize model name to standard format (name:tag without hash).
    
    Args:
        model_name: Model name in any format
        
    Returns:
        str: Normalized model name
    """
    # Handle name:tag:hash format
    if model_name.count(":") > 1:
        parts = model_name.split(":", 2)
        return f"{parts[0]}:{parts[1]}"
    
    # Handle name:tag format
    return model_name


def model_name_matches(requested_model: str, available_model: str) -> bool:
    """
    Check if a requested model name matches an available model.
    
    Args:
        requested_model: Requested model name (e.g., "llama3.2:3b")
        available_model: Available model name (e.g., "llama3.2:3b:a80c4f17acd5")
        
    Returns:
        bool: True if models match
    """
    # Normalize both names to name:tag format
    requested = normalize_model_name(requested_model)
    available = normalize_model_name(available_model)
    
    # Direct match
    if requested == available:
        return True
    
    # If tag is 'latest', it might match any tag
    if requested.endswith(":latest"):
        name = requested.split(":", 1)[0]
        available_name = available.split(":", 1)[0]
        return name == available_name
    
    return False


def find_matching_model(model_name: str, available_models: List[str]) -> Optional[str]:
    """
    Find a matching model in the list of available models.
    
    Args:
        model_name: Requested model name
        available_models: List of available models
        
    Returns:
        Optional[str]: Matching model name or None if not found
    """
    for available in available_models:
        if model_name_matches(model_name, available):
            return available
    
    return None


def get_model_details(model_name: str) -> Optional[Dict]:
    """
    Get details about a specific model.
    
    Args:
        model_name: Model name in format "name:tag"
        
    Returns:
        Optional[Dict]: Model details or None if not found
    """
    if not is_ollama_running():
        if not start_ollama():
            logger.error("Ollama must be running to get model details")
            return None
    
    try:
        # Try to use Ollama API to get model details
        import urllib.request
        import json
        
        # Split model name into name and tag
        if ":" in model_name:
            name, tag = model_name.split(":", 1)
        else:
            name, tag = model_name, "latest"
        
        try:
            url = f"{OLLAMA_API_ENDPOINT}/show?name={name}:{tag}"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            logger.debug(f"Error using API to get model details: {str(e)}")
            # Fall back to CLI method
        
        # Fall back to using Ollama CLI
        result = subprocess.run(
            ["ollama", "show", model_name],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception if model doesn't exist
        )
        
        if result.returncode == 0:
            # Try to parse the output as JSON
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not JSON, create a simplified dict
                return {
                    "name": name,
                    "tag": tag,
                    "details": result.stdout
                }
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting model details for {model_name}: {str(e)}")
        return None


def download_model(model_name: str, force: bool = False) -> bool:
    """
    Download a model using Ollama CLI.
    
    Args:
        model_name: Model name in format "name:tag"
        force: Force re-download even if model is already installed
        
    Returns:
        bool: True if download succeeded or model is already installed
    """
    # Check if already installed
    installed_models = list_installed_models()
    for installed in installed_models:
        if model_name_matches(model_name, installed):
            if not force:
                logger.info(f"Model {model_name} is already installed as {installed}")
                return True
            break
    
    logger.info(f"Downloading model {model_name}")
    
    if not is_ollama_running():
        if not start_ollama():
            logger.error("Ollama must be running to download models")
            return False
    
    # Check if model exists in registry before downloading
    available_models = list_available_models()
    if not available_models:
        logger.warning("Could not retrieve available models list")
    else:
        matching_model = find_matching_model(model_name, available_models)
        if not matching_model:
            logger.error(f"Model {model_name} not found in Ollama registry")
            # Suggest alternative models
            logger.info("Available models:")
            for available_model in available_models[:5]:  # Show up to 5 alternatives
                logger.info(f"  - {available_model}")
            return False
        elif matching_model != model_name:
            logger.info(f"Found matching model: {matching_model}")
    
    try:
        # Use subprocess with real-time output to show progress
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Process output line by line for progress reporting
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                # Look for progress information
                if "%" in line:
                    logger.info(line)
                else:
                    logger.debug(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code == 0:
            logger.info(f"Successfully downloaded model {model_name}")
            return True
        else:
            logger.error(f"Failed to download model {model_name}")
            return False
    
    except Exception as e:
        logger.error(f"Error downloading model {model_name}: {str(e)}")
        return False


def verify_model(model_name: str) -> bool:
    """
    Verify that a model is correctly installed and functional.
    
    Args:
        model_name: Model name in format "name:tag"
        
    Returns:
        bool: True if model is verified as working
    """
    if not is_ollama_running():
        if not start_ollama():
            logger.error("Ollama must be running to verify models")
            return False
    
    logger.info(f"Verifying model {model_name}")
    
    try:
        # First check if model is in the installed list
        installed_models = list_installed_models()
        if model_name not in installed_models:
            logger.error(f"Model {model_name} is not installed")
            return False
        
        # Check model details and parameters
        details = get_model_details(model_name)
        if not details:
            logger.error(f"Could not retrieve details for model {model_name}")
            return False
        
        # Optional: Perform a simple inference test
        logger.info(f"Testing model {model_name} with simple prompt")
        test_result = subprocess.run(
            ["ollama", "run", model_name, "Hello, how are you?", "--nowordwrap"],
            capture_output=True,
            text=True,
            timeout=30,  # Set timeout to prevent hanging
            check=False
        )
        
        if test_result.returncode != 0:
            logger.error(f"Model {model_name} failed test inference")
            logger.debug(f"Error: {test_result.stderr}")
            return False
        
        logger.info(f"Model {model_name} verified successfully")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error(f"Verification timed out for model {model_name}")
        return False
    except Exception as e:
        logger.error(f"Error verifying model {model_name}: {str(e)}")
        return False


def setup_models(models: List[str] = None, force: bool = False, verify: bool = True) -> Dict[str, bool]:
    """
    Download and verify specified models.
    
    Args:
        models: List of model names to download (default: DEFAULT_MODELS)
        force: Force re-download even if models are already installed
        verify: Verify models after download
        
    Returns:
        Dict[str, bool]: Dictionary of model names and success status
    """
    models = models or DEFAULT_MODELS
    results = {}
    
    # Ensure Ollama is running
    if not is_ollama_running():
        if not start_ollama():
            logger.error("Failed to start Ollama. Cannot download models.")
            return {model: False for model in models}
    
    # Get available models
    available_models = list_available_models()
    if not available_models:
        logger.warning("Could not retrieve list of available models")
    
    # Process each model
    for model in models:
        logger.info(f"Setting up model: {model}")
        
        # Check if model is available
        if available_models:
            matching_model = find_matching_model(model, available_models)
            if not matching_model:
                logger.warning(f"Model {model} not found in available models. Skipping.")
                results[model] = False
                continue
        
        # Download model
        download_success = download_model(model, force=force)
        
        # Verify model if enabled and download was successful
        if download_success and verify:
            verify_success = verify_model(model)
        else:
            verify_success = download_success or False
        
        # Store result
        results[model] = download_success and (verify_success if verify else True)
        
        if results[model]:
            logger.info(f"Model {model} setup completed successfully")
        else:
            logger.error(f"Model {model} setup failed")
    
    return results


def main():
    """Main entry point for model download script."""
    parser = argparse.ArgumentParser(description='Download and manage models for LangChain and Ollama')
    parser.add_argument('--models', nargs='+', help='Models to download (format: name:tag)')
    parser.add_argument('--force', action='store_true', help='Force re-download even if models are already installed')
    parser.add_argument('--no-verify', action='store_true', help='Skip model verification after download')
    parser.add_argument('--list', action='store_true', help='List available models and exit')
    parser.add_argument('--list-installed', action='store_true', help='List installed models and exit')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle list operations
    if args.list:
        logger.info("Available models:")
        models = list_available_models()
        for model in models:
            print(f"  {model}")
        return 0
    
    if args.list_installed:
        logger.info("Installed models:")
        models = list_installed_models()
        for model in models:
            print(f"  {model}")
        return 0
    
    # Download models
    models = args.models or DEFAULT_MODELS
    results = setup_models(
        models=models,
        force=args.force,
        verify=not args.no_verify
    )
    
    # Summarize results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Model setup completed: {success_count}/{len(results)} successful")
    
    # Return appropriate exit code
    if all(results.values()):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
