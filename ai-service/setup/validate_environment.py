#!/usr/bin/env python3
"""
Validate Python Environment for LangChain and Ollama Integration

This script performs validation checks on the Python environment to ensure
it meets the requirements for running LangChain with Ollama integration.

Requirements:
- Python 3.7 or higher
- Ability to install required packages
"""

import sys
import os
import platform
import subprocess
import logging
from typing import Tuple, Dict, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('environment-validator')

# Minimum required Python version
REQUIRED_PYTHON_VERSION = (3, 7)
RECOMMENDED_PYTHON_VERSION = (3, 10)


def check_python_version() -> Tuple[bool, str]:
    """
    Check if the current Python version meets the minimum requirement.
    
    Returns:
        Tuple[bool, str]: (True if version is sufficient, Message with version details)
    """
    current_version = sys.version_info[:2]
    
    if current_version < REQUIRED_PYTHON_VERSION:
        return False, f"Python version {'.'.join(map(str, current_version))} detected. " \
                      f"Version {'.'.join(map(str, REQUIRED_PYTHON_VERSION))}+ is required."
    
    if current_version < RECOMMENDED_PYTHON_VERSION:
        return True, f"Python version {'.'.join(map(str, current_version))} detected. " \
                    f"This meets the minimum requirement, but version " \
                    f"{'.'.join(map(str, RECOMMENDED_PYTHON_VERSION))}+ is recommended for optimal performance."
    
    return True, f"Python version {'.'.join(map(str, current_version))} detected. This meets the requirements."


def check_pip_installation() -> Tuple[bool, str]:
    """
    Check if pip is installed and accessible.
    
    Returns:
        Tuple[bool, str]: (True if pip is installed, Message with pip details)
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', '--version'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True, f"pip is installed: {result.stdout.strip()}"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, "pip is not installed or not accessible. Please install pip to continue."


def check_virtualenv() -> Tuple[bool, str]:
    """
    Check if running in a virtual environment.
    
    Returns:
        Tuple[bool, str]: (True if in venv, Message with environment details)
    """
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        return True, f"Running in virtual environment: {sys.prefix}"
    else:
        return False, "Not running in a virtual environment. It's recommended to use a virtual environment."


def check_disk_space(required_mb: int = 1000) -> Tuple[bool, str]:
    """
    Check if there's enough disk space available.
    
    Args:
        required_mb: Required space in megabytes
        
    Returns:
        Tuple[bool, str]: (True if enough space, Message with space details)
    """
    try:
        if platform.system() == 'Windows':
            free_bytes = os.statvfs(os.path.abspath(os.sep)).f_frsize * os.statvfs(os.path.abspath(os.sep)).f_bavail
        else:
            free_bytes = os.statvfs(os.path.dirname(os.path.abspath(__file__))).f_frsize * \
                        os.statvfs(os.path.dirname(os.path.abspath(__file__))).f_bavail
        
        free_mb = free_bytes / (1024 * 1024)
        
        if free_mb < required_mb:
            return False, f"Insufficient disk space. {free_mb:.2f}MB available, {required_mb}MB required."
        else:
            return True, f"Sufficient disk space available: {free_mb:.2f}MB"
    except Exception as e:
        return False, f"Error checking disk space: {str(e)}"


def run_environment_validation() -> Dict[str, Tuple[bool, str]]:
    """
    Run all environment validation checks.
    
    Returns:
        Dict[str, Tuple[bool, str]]: Dictionary of check results
    """
    results = {}
    
    logger.info("Starting environment validation for LangChain and Ollama integration")
    
    # Check Python version
    python_check, python_message = check_python_version()
    results['python_version'] = (python_check, python_message)
    logger.info(python_message)
    
    # Check pip installation
    pip_check, pip_message = check_pip_installation()
    results['pip_installation'] = (pip_check, pip_message)
    logger.info(pip_message)
    
    # Check virtual environment
    venv_check, venv_message = check_virtualenv()
    results['virtual_env'] = (venv_check, venv_message)
    logger.info(venv_message)
    
    # Check disk space
    space_check, space_message = check_disk_space()
    results['disk_space'] = (space_check, space_message)
    logger.info(space_message)
    
    return results


def summarize_validation(results: Dict[str, Tuple[bool, str]]) -> bool:
    """
    Summarize validation results and determine if the environment is ready.
    
    Args:
        results: Dictionary of validation results
        
    Returns:
        bool: True if environment is ready, False otherwise
    """
    critical_checks = ['python_version', 'pip_installation', 'disk_space']
    warning_checks = ['virtual_env']
    
    # Check if any critical checks failed
    failed_critical = [name for name in critical_checks if not results.get(name, (False, ''))[0]]
    
    # Check if any warning checks failed
    failed_warnings = [name for name in warning_checks if not results.get(name, (False, ''))[0]]
    
    if failed_critical:
        logger.error("Environment validation failed! The following critical requirements were not met:")
        for check in failed_critical:
            logger.error(f" - {results[check][1]}")
        return False
    
    if failed_warnings:
        logger.warning("Environment validation passed with warnings:")
        for check in failed_warnings:
            logger.warning(f" - {results[check][1]}")
    
    if not failed_critical and not failed_warnings:
        logger.info("All environment validation checks passed!")
    else:
        logger.info("Critical environment validation checks passed with warnings.")
    
    return True


def main():
    """Main entry point for environment validation."""
    results = run_environment_validation()
    environment_ready = summarize_validation(results)
    
    if not environment_ready:
        logger.error("Environment validation failed. Please address the issues above before continuing.")
        sys.exit(1)
    else:
        logger.info("Environment validation successful. You can proceed with the setup.")
        sys.exit(0)


if __name__ == "__main__":
    main()
