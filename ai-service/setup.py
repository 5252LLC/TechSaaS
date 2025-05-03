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
                   [--skip-models] [--skip-model-verify] [--force-reinstall]
                   [--update-ollama-only] [--models] [--verbose] [--skip-tests]
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

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Set up LangChain and Ollama")
    
    # Skip options
    parser.add_argument("--skip-environment-check", action="store_true", help="Skip environment validation")
    parser.add_argument("--skip-dependencies", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama setup")
    parser.add_argument("--skip-models", action="store_true", help="Skip model download")
    parser.add_argument("--skip-model-verify", action="store_true", help="Skip model verification")
    parser.add_argument("--skip-tests", action="store_true", help="Skip integration tests")
    
    # Force options
    parser.add_argument("--force-reinstall", action="store_true", help="Force reinstallation of dependencies")
    parser.add_argument("--update-ollama-only", action="store_true", help="Only update Ollama, skip other steps")
    
    # Model options
    parser.add_argument("--models", type=str, help="Comma-separated list of models to download (default: llama3:8b,phi3:mini)")
    
    # Other options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    # Parse arguments
    return parser.parse_args()


def setup_logging(verbose):
    """Configure logging."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")


def print_banner():
    """Print the setup banner."""
    print("\n" + "=" * 80)
    print("TechSaaS Platform - LangChain and Ollama Integration Setup".center(80))
    print("=" * 80 + "\n")


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


def validate_environment():
    """Run environment validation."""
    return run_step(
        "Environment validation",
        [sys.executable, os.path.join(SETUP_DIR, "setup/validate_environment.py")]
    )


def install_dependencies(args):
    """Install required dependencies."""
    cmd = [sys.executable, os.path.join(SETUP_DIR, "setup/install_dependencies.py")]
    if args.force_reinstall:
        cmd.append("--upgrade")
    
    return run_step(
        "Dependency installation",
        cmd
    )


def setup_ollama(args):
    """
    Run the Ollama setup script to install and configure Ollama.
    
    Returns:
        bool: True if Ollama setup was successful
    """
    logging.info("Running Ollama setup...")
    
    # Prepare command to run the Ollama setup script
    cmd = [sys.executable, os.path.join(SETUP_DIR, "setup/setup_ollama.py")]
    
    # Add arguments
    if args.verbose:
        cmd.append("--verbose")
    
    if args.force_reinstall:
        cmd.append("--force")
    
    if args.update_ollama_only:
        cmd.append("--update-only")
    
    try:
        # Run the Ollama setup script
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Log output at debug level
        for line in result.stdout.splitlines():
            logging.debug(line)
        
        logging.info("Ollama setup completed successfully")
        return True
    
    except subprocess.CalledProcessError as e:
        logging.error(f"Ollama setup failed with exit code {e.returncode}")
        if e.stderr:
            logging.error(f"Error output: {e.stderr}")
        logging.warning("Ollama setup encountered issues. You may need to install Ollama manually. Continuing with remaining setup steps...")
        return False


def download_models(args):
    """
    Download and verify required models for LangChain and Ollama.
    
    Returns:
        bool: True if model download was successful
    """
    try:
        # If the download_models.py module exists, use it
        from setup.download_models import download_required_models
        
        # Get the models to download
        models = []
        if args.models:
            models = [model.strip() for model in args.models.split(",")]
        
        return download_required_models(
            models=models,
            force=args.force_reinstall,
            skip_verify=args.skip_model_verify,
            verbose=args.verbose
        )
    except ImportError:
        # Fall back to a simple model download using run_step
        logging.warning("download_models.py not found, falling back to basic model download")
        
        # Default models if not specified
        models = args.models if args.models else "llama3:8b,phi3:mini"
        models_list = [model.strip() for model in models.split(",")]
        
        success = True
        for model in models_list:
            logging.info(f"Downloading model: {model}")
            cmd = ["ollama", "pull", model]
            step_success = run_step(f"Download model {model}", cmd, exit_on_error=False)
            success = success and step_success
            
        return success


def run_integration_tests(args):
    """
    Run integration tests for LangChain and Ollama.
    
    Returns:
        bool: True if integration tests were successful
    """
    try:
        # If the test_integration.py module exists, use it
        from setup.test_integration import run_integration_tests
        
        # Get the models to test with
        models = []
        if args.models:
            models = [model.strip() for model in args.models.split(",")]
        
        logging.info("Running LangChain and Ollama integration tests...")
        success, message = run_integration_tests(models)
        
        if success:
            logging.info("Integration tests passed successfully!")
        else:
            logging.error(f"Integration tests failed: {message}")
        
        return success
    
    except ImportError:
        # Fall back to a simple test command
        logging.warning("test_integration.py not found, falling back to basic integration test")
        
        # Try to find the test script
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "test_langchain_ollama.py")
        
        if os.path.exists(test_script):
            cmd = [sys.executable, test_script]
            return run_step("Integration tests", cmd, exit_on_error=False)
        else:
            logging.error(f"Test script not found: {test_script}")
            logging.error("Please ensure the test script exists or run with --skip-tests")
            return False


def main():
    """Main entry point for LangChain and Ollama setup."""
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging
    setup_logging(args.verbose)
    
    # Print banner
    print_banner()
    
    # Setup steps
    environment_ok = True
    dependencies_ok = True
    ollama_ok = True
    models_ok = True
    tests_ok = True
    
    # Step 1: Environment validation
    if not args.skip_environment_check:
        environment_ok = validate_environment()
    else:
        logging.info("Skipping environment validation (--skip-environment-check)")
    
    # Step 2: Dependency installation
    if environment_ok and not args.skip_dependencies and not args.update_ollama_only:
        dependencies_ok = install_dependencies(args)
    elif args.skip_dependencies:
        logging.info("Skipping dependency installation (--skip-dependencies)")
    elif args.update_ollama_only:
        logging.info("Skipping dependency installation (--update-ollama-only)")
    
    # Step 3: Ollama setup
    if environment_ok and not args.skip_ollama:
        ollama_ok = setup_ollama(args)
    elif args.skip_ollama:
        logging.info("Skipping Ollama setup (--skip-ollama)")
    
    # Step 4: Model download
    if environment_ok and dependencies_ok and ollama_ok and not args.skip_models and not args.update_ollama_only:
        models_ok = download_models(args)
    elif args.skip_models:
        logging.info("Skipping model download (--skip-models)")
    elif args.update_ollama_only:
        logging.info("Skipping model download (--update-ollama-only)")
    
    # Step 5: Integration tests
    if environment_ok and dependencies_ok and ollama_ok and models_ok and not args.skip_tests and not args.update_ollama_only:
        tests_ok = run_integration_tests(args)
    elif args.skip_tests:
        logging.info("Skipping integration tests (--skip-tests)")
    elif args.update_ollama_only:
        logging.info("Skipping integration tests (--update-ollama-only)")
    
    # Summary
    if args.update_ollama_only:
        logging.info("Ollama update process complete")
    else:
        status_message = "Setup process completed"
        if not args.skip_environment_check:
            status_message += " with environment validation"
        if not args.skip_dependencies:
            status_message += ", dependency installation"
        if not args.skip_ollama:
            status_message += ", and Ollama setup"
            if not ollama_ok:
                status_message += " (with issues)"
        if not args.skip_models:
            status_message += ", and model download"
            if not models_ok:
                status_message += " (with issues)"
        if not args.skip_tests:
            status_message += ", and integration testing"
            if not tests_ok:
                status_message += " (with issues)"
        
        logging.info(status_message)
        logging.info("LangChain and Ollama integration setup is now complete")
    
    print("\nSetup process completed successfully!")
    
    # Return success code only if all enabled steps succeeded
    success = True
    if not args.skip_environment_check and not environment_ok:
        success = False
    if not args.skip_dependencies and not args.update_ollama_only and not dependencies_ok:
        success = False
    if not args.skip_ollama and not ollama_ok:
        success = False
    if not args.skip_models and not args.update_ollama_only and not models_ok:
        success = False
    if not args.skip_tests and not args.update_ollama_only and not tests_ok:
        success = False
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
