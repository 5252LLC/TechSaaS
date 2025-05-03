#!/usr/bin/env python3
"""
Test script for LangChain and Ollama integration.
This script verifies that the LangChain and Ollama setup is working correctly.
"""

import os
import sys
import time
import argparse
import logging
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LangChain-Ollama-Test")

try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_community.llms import Ollama
    logger.info("Successfully imported LangChain and Ollama modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Please ensure LangChain and Ollama are installed.")
    logger.error("Run: pip install langchain langchain-community ollama")
    sys.exit(1)

def check_ollama_service() -> bool:
    """Check if Ollama service is running."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            logger.info(f"Ollama service is running. Version: {response.json().get('version', 'unknown')}")
            return True
        else:
            logger.error(f"Ollama service returned status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to connect to Ollama service: {e}")
        logger.info("Starting Ollama service...")
        
        try:
            import subprocess
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("Waiting for Ollama service to start...")
            time.sleep(5)  # Give it some time to start
            return check_ollama_service()  # Recursive check
        except Exception as start_error:
            logger.error(f"Failed to start Ollama service: {start_error}")
            return False

def list_available_models() -> List[str]:
    """List available Ollama models."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = [model["name"] for model in response.json().get("models", [])]
            logger.info(f"Available models: {', '.join(models) if models else 'None'}")
            return models
        else:
            logger.error(f"Failed to retrieve models: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

def test_ollama_direct() -> bool:
    """Test direct Ollama API."""
    try:
        import requests
        logger.info("Testing direct Ollama API...")
        
        # Get available models
        models = list_available_models()
        if not models:
            logger.error("No models available in Ollama")
            return False
        
        # Use the first available model
        model_name = models[0]
        logger.info(f"Testing with model: {model_name}")
        
        # Generate a simple response
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": "Hello, how are you?", "stream": False}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Ollama API test successful. Response: {result.get('response', '')[:100]}...")
            return True
        else:
            logger.error(f"Ollama API test failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error testing Ollama API: {e}")
        return False

def test_langchain_ollama(model_name: Optional[str] = None) -> bool:
    """Test LangChain with Ollama integration."""
    try:
        logger.info("Testing LangChain with Ollama integration...")
        
        # If model name not specified, use the first available model
        if not model_name:
            models = list_available_models()
            if not models:
                logger.error("No models available in Ollama")
                return False
            model_name = models[0]
        
        logger.info(f"Using model: {model_name}")
        
        # Initialize Ollama with the model
        llm = Ollama(model=model_name, temperature=0.7)
        
        # Create a simple prompt template
        template = """Question: {question}

        Answer:"""
        
        prompt = PromptTemplate(template=template, input_variables=["question"])
        
        # Create the LLMChain
        llm_chain = LLMChain(prompt=prompt, llm=llm)
        
        # Run the chain
        question = "What is the capital of France?"
        logger.info(f"Testing question: {question}")
        
        result = llm_chain.invoke({"question": question})
        logger.info(f"LangChain-Ollama test successful")
        logger.info(f"Result: {result['text'][:500]}...")
        return True
    except Exception as e:
        logger.error(f"Error testing LangChain with Ollama: {e}")
        return False

def run_test_suite(args: argparse.Namespace) -> bool:
    """Run the complete test suite."""
    results = []
    
    # Step 1: Check if Ollama service is running
    logger.info("Step 1: Checking Ollama service...")
    service_check = check_ollama_service()
    results.append(("Ollama Service Check", service_check))
    if not service_check:
        logger.error("Ollama service check failed, cannot proceed with further tests")
        return False
    
    # Step 2: Test direct Ollama API
    logger.info("Step 2: Testing direct Ollama API...")
    ollama_api_test = test_ollama_direct()
    results.append(("Direct Ollama API Test", ollama_api_test))
    
    # Step 3: Test LangChain with Ollama
    logger.info("Step 3: Testing LangChain with Ollama integration...")
    langchain_test = test_langchain_ollama(args.model)
    results.append(("LangChain-Ollama Integration Test", langchain_test))
    
    # Print summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    all_passed = True
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("=" * 50)
    if all_passed:
        logger.info("All tests PASSED! LangChain and Ollama are successfully integrated.")
    else:
        logger.error("Some tests FAILED. Please check the logs for details.")
    
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Test LangChain and Ollama integration")
    parser.add_argument("--model", type=str, help="Specific model to test with")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Run tests
    success = run_test_suite(args)
    
    # Exit with appropriate code for external scripts to check
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
