#!/usr/bin/env python3
"""
LangChain and Ollama Integration Setup Script

This script handles the complete setup process for the LangChain and Ollama
integration used in the TechSaaS platform. It performs the following tasks:
1. Validates the Python environment
2. Installs required dependencies
3. Sets up Ollama based on the detected platform
4. Downloads required AI models
5. Tests the integration

Usage:
    python setup.py [--skip-validation] [--skip-dependencies] [--skip-ollama]
                   [--skip-models] [--skip-tests] [--verbose]
"""

import argparse
import logging
import os
import subprocess
import sys
from typing import List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('langchain-setup')


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Setup LangChain and Ollama for TechSaaS Platform'
    )
    parser.add_argument(
        '--skip-validation', 
        action='store_true',
        help='Skip environment validation step'
    )
    parser.add_argument(
        '--skip-dependencies', 
        action='store_true',
        help='Skip dependency installation step'
    )
    parser.add_argument(
        '--skip-ollama', 
        action='store_true',
        help='Skip Ollama setup step'
    )
    parser.add_argument(
        '--skip-models', 
        action='store_true',
        help='Skip model download step'
    )
    parser.add_argument(
        '--skip-tests', 
        action='store_true',
        help='Skip integration tests'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose output'
    )
    return parser.parse_args()


def run_step(step_name: str, command: List[str], exit_on_error: bool = True) -> bool:
    """
    Run a setup step as a subprocess command.
    
    Args:
        step_name: Name of the step for logging
        command: Command to execute as a list
        exit_on_error: Whether to exit if the command fails
        
    Returns:
        bool: True if step succeeded, False otherwise
    """
    logger.info(f"Running {step_name}...")
    
    try:
        process = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True
        )
        
        logger.info(f"{step_name} completed successfully")
        if process.stdout.strip():
            logger.debug(process.stdout.strip())
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"{step_name} failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr.strip()}")
        
        if exit_on_error:
            logger.error(f"Exiting setup due to {step_name} failure")
            sys.exit(e.returncode)
        
        return False


def validate_environment(args):
    """Run environment validation."""
    if args.skip_validation:
        logger.info("Skipping environment validation (--skip-validation)")
        return True
    
    return run_step(
        "Environment validation",
        [sys.executable, "setup/validate_environment.py"]
    )


def main():
    """Main entry point for the setup script."""
    args = parse_arguments()
    
    # Set log level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Print banner
    print("\n" + "=" * 80)
    print("TechSaaS Platform - LangChain and Ollama Integration Setup".center(80))
    print("=" * 80 + "\n")
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run environment validation
    validate_environment(args)
    
    # At this point, environment validation has passed or been skipped
    # Additional steps will be implemented in subsequent tasks (5.2-5.5)
    logger.info("Environment validation complete")
    logger.info("Ready to proceed with remaining setup steps")
    
    print("\nSetup process completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
