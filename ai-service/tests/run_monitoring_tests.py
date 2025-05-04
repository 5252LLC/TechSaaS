#!/usr/bin/env python
"""
Test Runner for TechSaaS Monitoring System

This script runs all the tests for the monitoring system components.
"""

import unittest
import os
import sys
import importlib.util

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the ai-service directory to the Python path
ai_service_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ai_service_dir not in sys.path:
    sys.path.insert(0, ai_service_dir)


def load_tests_from_module(file_path, pattern):
    """Load test cases from a module file."""
    module_name = os.path.basename(file_path).replace('.py', '')
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def run_monitoring_tests():
    """Run all monitoring system tests."""
    # Find all monitoring test files
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [
        os.path.join(test_dir, f) 
        for f in os.listdir(test_dir) 
        if f.startswith('test_monitoring_') and f.endswith('.py')
    ]
    
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add tests from each file
    for test_file in test_files:
        try:
            print(f"Loading tests from {os.path.basename(test_file)}")
            file_tests = load_tests_from_module(test_file, 'test_*')
            test_suite.addTests(file_tests)
        except Exception as e:
            print(f"Error loading tests from {test_file}: {e}")
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_monitoring_tests()
    sys.exit(not success)
