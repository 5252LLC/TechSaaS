#!/usr/bin/env python3
"""
Integration test runner for LangChain and Ollama.
This script integrates with the setup process to verify correct installation.
"""

import os
import sys
import subprocess
import importlib.util
import logging
from typing import Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Integration-Test-Runner")

def check_dependencies() -> bool:
    """Check if all required dependencies are installed."""
    required_modules = [
        "langchain", 
        "langchain_community", 
        "ollama",
        "requests"
    ]
    
    missing = []
    for module in required_modules:
        if importlib.util.find_spec(module) is None:
            missing.append(module)
    
    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        logger.info("Please run the setup script with the --install-dependencies flag")
        return False
    
    return True

def run_integration_tests(models: list = None) -> Tuple[bool, str]:
    """
    Run the LangChain-Ollama integration tests.
    
    Args:
        models: Optional list of models to test with.
               If None, the test will use whatever models are available.
    
    Returns:
        Tuple of (success, message)
    """
    if not check_dependencies():
        return False, "Dependencies check failed. Please install required packages."
    
    # Get the path to the test script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_script = os.path.join(os.path.dirname(script_dir), "tests", "test_langchain_ollama.py")
    
    # Ensure the test script exists
    if not os.path.exists(test_script):
        logger.error(f"Test script not found: {test_script}")
        return False, f"Test script not found: {test_script}"
    
    try:
        # Make the script executable
        try:
            os.chmod(test_script, 0o755)
        except Exception as e:
            logger.warning(f"Could not make test script executable: {e}")
        
        # Build command
        cmd = [sys.executable, test_script, "--verbose"]
        
        # If a specific model is requested, add it to the command
        if models and isinstance(models, list) and len(models) > 0:
            cmd.extend(["--model", models[0]])  # Use the first model in the list
        
        # Run the test script
        logger.info(f"Running integration tests with command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        stdout_lines = []
        stderr_lines = []
        
        def process_stream(stream, lines_list):
            for line in stream:
                print(line, end='')  # Print in real-time
                lines_list.append(line)
                if "All tests PASSED!" in line:
                    return True
                if "Some tests FAILED" in line:
                    return False
            return None
        
        # Process output as it becomes available
        while process.poll() is None:
            success = process_stream(process.stdout, stdout_lines)
            if success is not None:
                # We found a definitive result, read any remaining output
                for line in process.stdout:
                    print(line, end='')
                    stdout_lines.append(line)
                break
        
        # Get return code
        return_code = process.wait()
        
        # Read any remaining output
        for line in process.stderr:
            print(line, end='')
            stderr_lines.append(line)
        
        # Determine success based on return code
        success = return_code == 0
        message = "Integration tests passed!" if success else "Integration tests failed."
        
        # Add details
        if stdout_lines:
            message += "\n\nOutput:\n" + "".join(stdout_lines[-10:])  # Last 10 lines
        if stderr_lines and not success:
            message += "\n\nErrors:\n" + "".join(stderr_lines)
        
        return success, message
    
    except Exception as e:
        error_message = f"Error running integration tests: {e}"
        logger.error(error_message)
        return False, error_message

def main():
    """Main entry point for running integration tests from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LangChain-Ollama integration tests")
    parser.add_argument("--model", type=str, help="Specific model to test with")
    args = parser.parse_args()
    
    models = [args.model] if args.model else None
    success, message = run_integration_tests(models)
    
    if not success:
        logger.error(message)
        sys.exit(1)
    else:
        logger.info(message)
        sys.exit(0)

if __name__ == "__main__":
    main()
