#!/usr/bin/env python3
"""
Manual Test Script for AI Endpoints

This script tests the AI endpoints implementation by making direct requests
to a running instance of the Flask API service.

Usage:
    1. Start the Flask API service
    2. Run this script to test the endpoints
    3. Check the output for any errors or unexpected responses
"""

import requests
import json
import sys
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5050"  # Change as needed
API_KEY = "test_api_key"  # Replace with a valid API key for testing

# Define colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(message, color=Colors.BLUE, bold=False):
    """Print colored message to terminal"""
    if bold:
        print(f"{color}{Colors.BOLD}{message}{Colors.END}")
    else:
        print(f"{color}{message}{Colors.END}")

def print_result(test_name, success, message=""):
    """Print test result with appropriate color"""
    if success:
        print_colored(f" {test_name}: PASSED", Colors.GREEN, bold=True)
    else:
        print_colored(f" {test_name}: FAILED - {message}", Colors.RED, bold=True)
    print()

def format_json(json_data):
    """Format JSON for pretty printing"""
    return json.dumps(json_data, indent=2)

def test_health_endpoint():
    """Test the health check endpoint"""
    print_colored("Testing Health Endpoint", Colors.BLUE, bold=True)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ai/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        success = (
            response.status_code == 200 and
            response.json().get("status") == "healthy"
        )
        
        print_result("Health Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Health Endpoint Test", False, str(e))
        return False

def test_models_endpoint():
    """Test the models endpoint"""
    print_colored("Testing Models Endpoint", Colors.BLUE, bold=True)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/ai/models",
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        success = (
            response.status_code == 200 and
            "models" in response.json()
        )
        
        print_result("Models Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Models Endpoint Test", False, str(e))
        return False

def test_chat_endpoint():
    """Test the chat endpoint"""
    print_colored("Testing Chat Endpoint", Colors.BLUE, bold=True)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "message": "Hello, how are you?",
        "history": [
            {"role": "system", "content": "You are a helpful assistant."}
        ],
        "model": "ollama/llama2",
        "options": {"temperature": 0.7}
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/chat",
            headers=headers,
            json=data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        json_response = response.json()
        success = (
            response.status_code == 200 and
            "response" in json_response and
            "model_used" in json_response
        )
        
        print_result("Chat Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Chat Endpoint Test", False, str(e))
        return False

def test_completion_endpoint():
    """Test the completion endpoint"""
    print_colored("Testing Completion Endpoint", Colors.BLUE, bold=True)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "prompt": "Once upon a time in a land far away,",
        "max_tokens": 100,
        "temperature": 0.7,
        "model": "ollama/llama2"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/completion",
            headers=headers,
            json=data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        json_response = response.json()
        success = (
            response.status_code == 200 and
            "completion" in json_response and
            "model_used" in json_response
        )
        
        print_result("Completion Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Completion Endpoint Test", False, str(e))
        return False

def test_analyze_endpoint():
    """Test the analyze endpoint"""
    print_colored("Testing Analyze Endpoint", Colors.BLUE, bold=True)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "content": "I absolutely love this product! It works perfectly and the customer service is excellent.",
        "task": "sentiment",
        "model": "ollama/llama2",
        "options": {"detailed": True}
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/analyze",
            headers=headers,
            json=data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        json_response = response.json()
        success = (
            response.status_code == 200 and
            "task" in json_response and
            "result" in json_response and
            "model_used" in json_response
        )
        
        print_result("Analyze Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Analyze Endpoint Test", False, str(e))
        return False

def test_batch_endpoint():
    """Test the batch processing endpoint"""
    print_colored("Testing Batch Processing Endpoint", Colors.BLUE, bold=True)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Explain neural networks in simple terms."
        ],
        "task": "completion",
        "task_params": {
            "model": "ollama/llama2",
            "max_tokens": 100
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/batch",
            headers=headers,
            json=data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {format_json(response.json())}")
        
        json_response = response.json()
        success = (
            response.status_code == 202 and
            "batch_id" in json_response and
            "status" in json_response and
            json_response["status"] == "pending"
        )
        
        print_result("Batch Processing Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Batch Processing Endpoint Test", False, str(e))
        return False

def test_example_beginner_endpoint():
    """Test the example beginner endpoint"""
    print_colored("Testing Example Beginner Endpoint", Colors.BLUE, bold=True)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ai/example/beginner")
        print(f"Status Code: {response.status_code}")
        
        # Print truncated response for readability
        json_response = response.json()
        if "examples" in json_response:
            print("Examples included in response")
        if "explanation" in json_response:
            print(f"Explanation length: {len(json_response['explanation'])} characters")
        
        success = (
            response.status_code == 200 and
            "examples" in json_response and
            "explanation" in json_response
        )
        
        print_result("Example Beginner Endpoint Test", success)
        return success
    except Exception as e:
        print_colored(f"Error: {str(e)}", Colors.RED)
        print_result("Example Beginner Endpoint Test", False, str(e))
        return False

def run_all_tests():
    """Run all endpoint tests"""
    print_colored("Starting AI Endpoint Tests", Colors.BOLD, bold=True)
    print_colored("================================\n", Colors.BOLD)
    
    results = {
        "health": test_health_endpoint(),
        "models": test_models_endpoint(),
        "chat": test_chat_endpoint(),
        "completion": test_completion_endpoint(),
        "analyze": test_analyze_endpoint(),
        "batch": test_batch_endpoint(),
        "example": test_example_beginner_endpoint()
    }
    
    # Print summary
    print_colored("\nTest Summary", Colors.BLUE, bold=True)
    print_colored("================================", Colors.BLUE)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        color = Colors.GREEN if result else Colors.RED
        print_colored(f"{test_name.capitalize()}: {status}", color)
    
    print_colored("================================", Colors.BLUE)
    print_colored(f"Total: {passed}/{total} tests passed", Colors.BOLD, bold=True)
    
    if passed == total:
        print_colored(" All tests passed! The AI endpoints are working correctly.", Colors.GREEN, bold=True)
    else:
        print_colored(f" {total - passed} tests failed. Please check the logs for details.", Colors.YELLOW, bold=True)
    
    return passed == total

if __name__ == "__main__":
    # Allow running individual tests
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        test_functions = {
            "health": test_health_endpoint,
            "models": test_models_endpoint,
            "chat": test_chat_endpoint,
            "completion": test_completion_endpoint,
            "analyze": test_analyze_endpoint,
            "batch": test_batch_endpoint,
            "example": test_example_beginner_endpoint
        }
        
        if test_name in test_functions:
            test_functions[test_name]()
        else:
            print_colored(f"Unknown test: {test_name}", Colors.RED)
            print_colored(f"Available tests: {', '.join(test_functions.keys())}", Colors.YELLOW)
    else:
        # Run all tests
        run_all_tests()
