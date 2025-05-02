#!/usr/bin/env python3
"""
Dependency Installation Script for LangChain and Ollama Integration

This script handles the installation of all required Python packages for
the LangChain and Ollama integration. It reads from requirements.txt,
installs each dependency using pip, and verifies the installations.

Requirements:
- Working pip installation
- Internet connection for package downloads
"""

import importlib
import logging
import os
import subprocess
import sys
from typing import Dict, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('dependency-installer')

# Core packages that must be importable after installation
CORE_PACKAGES = [
    'langchain',
    'pydantic',
    'numpy',
    'requests',
    'dotenv',
    'ollama'
]


def read_requirements(file_path: str = 'requirements.txt') -> List[str]:
    """
    Read requirements from the requirements.txt file.
    
    Args:
        file_path: Path to the requirements file
        
    Returns:
        List[str]: List of package requirements
    """
    try:
        with open(file_path, 'r') as f:
            # Filter out comments and empty lines
            requirements = [
                line.strip() for line in f 
                if line.strip() and not line.strip().startswith('#')
            ]
        
        logger.info(f"Read {len(requirements)} package requirements from {file_path}")
        return requirements
    
    except FileNotFoundError:
        logger.error(f"Requirements file not found: {file_path}")
        sys.exit(1)


def install_packages(requirements: List[str], upgrade: bool = False) -> List[Tuple[str, bool, str]]:
    """
    Install packages using pip.
    
    Args:
        requirements: List of package requirements
        upgrade: Whether to upgrade existing packages
        
    Returns:
        List[Tuple[str, bool, str]]: List of (package, success, message) tuples
    """
    results = []
    
    for req in requirements:
        package_name = req.split('>=')[0].split('==')[0].strip()
        logger.info(f"Installing {package_name}...")
        
        try:
            cmd = [sys.executable, '-m', 'pip', 'install']
            
            if upgrade:
                cmd.append('--upgrade')
            
            cmd.append(req)
            
            process = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            results.append((package_name, True, f"Successfully installed {package_name}"))
            logger.info(f"Successfully installed {package_name}")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install {package_name}: {e.stderr}"
            results.append((package_name, False, error_msg))
            logger.error(error_msg)
    
    return results


def verify_installations(core_packages: List[str] = CORE_PACKAGES) -> Dict[str, bool]:
    """
    Verify that core packages can be imported.
    
    Args:
        core_packages: List of core package names to verify
        
    Returns:
        Dict[str, bool]: Dictionary of package verification results
    """
    verification_results = {}
    
    for package in core_packages:
        try:
            # Handle special case for python-dotenv
            if package == 'dotenv':
                package_to_import = 'dotenv'
            else:
                package_to_import = package
                
            importlib.import_module(package_to_import)
            verification_results[package] = True
            logger.info(f"Successfully verified import of {package}")
            
        except ImportError:
            verification_results[package] = False
            logger.error(f"Failed to import {package}")
    
    return verification_results


def summarize_installation(
    install_results: List[Tuple[str, bool, str]],
    verify_results: Dict[str, bool]
) -> bool:
    """
    Summarize installation and verification results.
    
    Args:
        install_results: Results from install_packages
        verify_results: Results from verify_installations
        
    Returns:
        bool: True if all core packages were successfully installed and verified
    """
    # Count successful installations
    successful_installs = sum(1 for _, success, _ in install_results if success)
    total_installs = len(install_results)
    
    # Count successful verifications
    successful_verifies = sum(1 for success in verify_results.values() if success)
    total_verifies = len(verify_results)
    
    # Log summary
    logger.info(f"Successfully installed {successful_installs}/{total_installs} packages")
    logger.info(f"Successfully verified {successful_verifies}/{total_verifies} core packages")
    
    # Check if all core packages were successfully verified
    all_verified = all(verify_results.values())
    
    if all_verified:
        logger.info("All core dependencies have been successfully installed and verified")
    else:
        failed_packages = [pkg for pkg, success in verify_results.items() if not success]
        logger.error(f"Failed to verify the following core packages: {', '.join(failed_packages)}")
    
    return all_verified


def install_dependencies(upgrade: bool = False) -> bool:
    """
    Run the full dependency installation process.
    
    Args:
        upgrade: Whether to upgrade existing packages
        
    Returns:
        bool: True if installation succeeded
    """
    logger.info("Starting dependency installation for LangChain and Ollama integration")
    
    # Get script directory and parent directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    # Read requirements
    requirements_path = os.path.join(parent_dir, 'requirements.txt')
    requirements = read_requirements(requirements_path)
    
    # Install packages
    install_results = install_packages(requirements, upgrade)
    
    # Verify installations
    verify_results = verify_installations()
    
    # Summarize installation
    success = summarize_installation(install_results, verify_results)
    
    if success:
        logger.info("Dependency installation completed successfully")
    else:
        logger.error("Dependency installation completed with errors")
    
    return success


def main():
    """Main entry point for dependency installation."""
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Install dependencies for LangChain and Ollama integration')
    parser.add_argument('--upgrade', action='store_true', help='Upgrade existing packages')
    args = parser.parse_args()
    
    # Run installation
    success = install_dependencies(upgrade=args.upgrade)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
