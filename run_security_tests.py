#!/usr/bin/env python3
"""
TechSaaS Automated Security Testing Script

This script provides a convenient way to run security tests for the TechSaaS platform.
It can be used both during development and in CI/CD pipelines.

Usage:
  ./run_security_tests.py [options]

Options:
  --all                Run all security tests
  --auth               Run authentication tests
  --auth-bypass        Run authentication bypass tests
  --injection          Run injection vulnerability tests
  --xss                Run cross-site scripting tests
  --csrf               Run CSRF protection tests
  --headers            Run security headers tests
  --session            Run session security tests
  --rate-limit         Run rate limiting tests
  --api [ENDPOINT]     Test specific API endpoint
  --report=FORMAT      Output format (text, json, html, junit)
  --output=FILE        Output file for report
  --ci                 Run in CI mode
  --verbose            Show verbose output
  --help               Show this help message

Examples:
  ./run_security_tests.py --all
  ./run_security_tests.py --auth --xss --report=html
  ./run_security_tests.py --api /api/v1/users --injection
"""

import sys
import os
import argparse
import subprocess
import time
import json
import webbrowser
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run TechSaaS security tests')
    
    parser.add_argument('--all', action='store_true', help='Run all security tests')
    parser.add_argument('--auth', action='store_true', help='Run authentication tests')
    parser.add_argument('--auth-bypass', action='store_true', help='Run authentication bypass tests')
    parser.add_argument('--injection', action='store_true', help='Run injection vulnerability tests')
    parser.add_argument('--xss', action='store_true', help='Run cross-site scripting tests')
    parser.add_argument('--csrf', action='store_true', help='Run CSRF protection tests')
    parser.add_argument('--headers', action='store_true', help='Run security headers tests')
    parser.add_argument('--session', action='store_true', help='Run session security tests')
    parser.add_argument('--rate-limit', action='store_true', help='Run rate limiting tests')
    parser.add_argument('--api', type=str, help='Test specific API endpoint')
    parser.add_argument('--report', type=str, choices=['text', 'json', 'html', 'junit'], 
                        default='text', help='Output format')
    parser.add_argument('--output', type=str, help='Output file for report')
    parser.add_argument('--ci', action='store_true', help='Run in CI mode')
    parser.add_argument('--verbose', action='store_true', help='Show verbose output')
    parser.add_argument('--help-security', action='store_true', help='Show security testing help')
    
    return parser.parse_args()

def run_security_tests(args):
    """Run security tests based on command line arguments"""
    
    # Build command for security test suite
    cmd = ['python3', 'ai-service/tests/security_test_suite.py']
    
    # Add test type arguments
    if args.all:
        cmd.append('--all')
    if args.auth:
        cmd.append('--auth')
    if args.injection:
        cmd.append('--injection')
    if args.xss:
        cmd.append('--xss')
    if args.csrf:
        cmd.append('--csrf')
    if args.headers:
        cmd.append('--headers')
    if args.session:
        cmd.append('--session')
    if args.rate_limit:
        cmd.append('--rate-limit')
    
    # Add report format
    if args.report:
        cmd.append(f'--report={args.report}')
    
    # Add CI mode if specified
    if args.ci:
        cmd.append('--ci')
    
    # Add verbose flag if specified
    if args.verbose:
        cmd.append('--verbose')
    
    # If no test type is specified, default to all
    if not any([args.all, args.auth, args.auth_bypass, args.injection, args.xss, 
                args.csrf, args.headers, args.session, args.rate_limit, args.api]):
        cmd.append('--all')
    
    # Run the security test suite
    print(f"Running security tests: {' '.join(cmd)}")
    
    start_time = time.time()
    process = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()
    
    # Process output
    output = process.stdout
    error = process.stderr
    
    # Write to output file if specified
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    
    # Print output
    print(output)
    if error:
        print("Errors:", file=sys.stderr)
        print(error, file=sys.stderr)
    
    # Print summary
    print(f"\nSecurity tests completed in {end_time - start_time:.2f} seconds")
    print(f"Exit code: {process.returncode}")
    
    # If HTML report was generated, open it
    if args.report == 'html' and not args.ci:
        report_file = 'security_test_report.html'
        if os.path.exists(report_file):
            print(f"Opening HTML report: {report_file}")
            try:
                webbrowser.open(f"file://{os.path.abspath(report_file)}")
            except:
                print(f"Could not open browser automatically. Please open {report_file} manually.")
    
    return process.returncode

def run_api_security_test(endpoint, args):
    """Run security tests targeting a specific API endpoint"""
    
    print(f"Running API security tests for endpoint: {endpoint}")
    
    # Import core test modules
    from ai_service.tests.security.test_authentication import AuthenticationSecurityTests
    from ai_service.tests.security.test_authorization import AuthorizationSecurityTests
    from ai_service.tests.security.test_injection import InjectionSecurityTests
    from ai_service.tests.security.test_xss import XSSSecurityTests
    
    # Create test methods for the specific endpoint
    test_methods = {}
    
    # Authentication tests
    if args.auth or args.all:
        test_methods['test_auth_bypass'] = f"""
            def test_auth_bypass(self):
                \"\"\"Test authentication bypass on {endpoint}\"\"\"
                
                # Try without authentication
                response = requests.get("{endpoint}")
                
                # Check response
                if 'protected' in "{endpoint}" or 'admin' in "{endpoint}":
                    self.assertNotEqual(response.status_code, 200,
                                    "Endpoint allowed unauthenticated access")
                    
                # Try with invalid token
                headers = self.headers.copy()
                headers['Authorization'] = "Bearer invalid_token"
                response = requests.get("{endpoint}", headers=headers)
                
                # Should reject invalid token
                if 'protected' in "{endpoint}" or 'admin' in "{endpoint}":
                    self.assertNotEqual(response.status_code, 200,
                                    "Endpoint accepted invalid token")
        """
    
    # Injection tests
    if args.injection or args.all:
        test_methods['test_injection'] = f"""
            def test_injection(self):
                \"\"\"Test injection vulnerabilities on {endpoint}\"\"\"
                
                # SQL injection payloads
                payloads = [
                    "' OR 1=1 --",
                    "'; DROP TABLE users; --",
                    "' UNION SELECT username,password FROM users --"
                ]
                
                for payload in payloads:
                    # Test in URL parameters
                    response = requests.get("{endpoint}?q=" + payload)
                    self.assertFalse(
                        self._contains_database_error(response),
                        f"Endpoint vulnerable to SQL injection: {{payload}}"
                    )
        """
    
    # XSS tests
    if args.xss or args.all:
        test_methods['test_xss'] = f"""
            def test_xss(self):
                \"\"\"Test XSS vulnerabilities on {endpoint}\"\"\"
                
                # XSS payloads
                payloads = [
                    "<script>alert('XSS')</script>",
                    "<img src=x onerror=alert('XSS')>",
                    "<svg onload=alert('XSS')>"
                ]
                
                for payload in payloads:
                    # Test in URL parameters
                    response = requests.get("{endpoint}?q=" + payload)
                    
                    # Check if the payload was reflected without encoding
                    self.assertNotIn(payload, response.text,
                                  f"Endpoint vulnerable to XSS: {{payload}}")
        """
    
    # Generate and run the tests
    import types
    import unittest
    
    # Create test cases for the endpoint
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    for test_class in [AuthenticationSecurityTests, InjectionSecurityTests, XSSSecurityTests]:
        # Create a subclass for this specific endpoint
        class_name = f"{test_class.__name__}_{endpoint.replace('/', '_')}"
        
        # Create class attributes and methods
        attrs = {
            'endpoint': endpoint,
            'setup_done': False
        }
        
        # Add the test methods
        for method_name, method_code in test_methods.items():
            if test_class == AuthenticationSecurityTests and method_name.startswith('test_auth'):
                exec(method_code, globals(), attrs)
            elif test_class == InjectionSecurityTests and method_name.startswith('test_injection'):
                exec(method_code, globals(), attrs)
            elif test_class == XSSSecurityTests and method_name.startswith('test_xss'):
                exec(method_code, globals(), attrs)
        
        # Create the class
        endpoint_test_class = type(class_name, (test_class,), attrs)
        
        # Add the tests to the suite
        endpoint_tests = test_loader.loadTestsFromTestCase(endpoint_test_class)
        test_suite.addTests(endpoint_tests)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(test_suite)
    
    # Return success status
    return 0 if result.wasSuccessful() else 1

def check_security_dependencies():
    """Check that all required dependencies for security testing are installed"""
    required_packages = ['requests', 'jwt', 'bs4', 'lxml']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages for security testing:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print(f"  pip3 install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Show help message if requested
    if args.help_security:
        print(__doc__)
        return 0
    
    # Check dependencies
    if not check_security_dependencies():
        return 1
    
    # Run API-specific tests if specified
    if args.api:
        return run_api_security_test(args.api, args)
    
    # Run general security tests
    return run_security_tests(args)

if __name__ == "__main__":
    sys.exit(main())
