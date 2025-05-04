"""
Security Headers Tests

This module tests the implementation of security headers in the TechSaaS platform.
It checks for proper configuration of:
- Content Security Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security (HSTS)
- Referrer-Policy
- Permissions-Policy
- X-XSS-Protection
"""

import unittest
import requests
import os
import sys
import re
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class SecurityHeadersTests(unittest.TestCase):
    """Test cases for security headers"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.auth_url = f"{self.base_url}/api/v1/auth/login"
        self.public_endpoint = f"{self.base_url}/api/v1/status"
        self.protected_endpoint = f"{self.base_url}/api/v1/protected/user-profile"
        
        # Test credentials
        self.valid_credentials = {
            "email": "test@example.com",
            "password": "SecureP@ssw0rd!"
        }
        
        # Set up headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TechSaaS-Security-Test/1.0',
        }
        
        # Endpoints to check
        self.test_endpoints = [
            self.public_endpoint,
            self.auth_url,
            self.protected_endpoint,
            f"{self.base_url}/api/v1/docs",
            f"{self.base_url}/",
            f"{self.base_url}/api/v1/dashboard",
        ]
        
        # Login to get authentication token for protected endpoints
        try:
            login_response = requests.post(
                self.auth_url, 
                headers=self.headers, 
                json=self.valid_credentials,
                timeout=5
            )
            
            if login_response.status_code == 200:
                token = login_response.json().get('access_token')
                if token:
                    self.auth_headers = self.headers.copy()
                    self.auth_headers['Authorization'] = f"Bearer {token}"
        except:
            # Continue without authentication if login fails
            self.auth_headers = self.headers.copy()
    
    def test_content_security_policy(self):
        """Test for proper Content-Security-Policy header"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertIn('Content-Security-Policy', response.headers, 
                            f"Missing Content-Security-Policy header on {endpoint}")
                
                csp = response.headers.get('Content-Security-Policy', '')
                
                # Check for essential CSP directives
                essential_directives = [
                    'default-src', 
                    'script-src', 
                    'style-src', 
                    'img-src',
                    'connect-src',
                    'frame-ancestors',
                    'form-action'
                ]
                
                for directive in essential_directives:
                    self.assertIn(directive, csp, 
                                f"Missing essential CSP directive '{directive}' on {endpoint}")
                
                # Check for unsafe configurations
                unsafe_patterns = [
                    "script-src 'unsafe-inline'",
                    "script-src 'unsafe-eval'",
                    "script-src *",
                    "style-src 'unsafe-inline'",
                    "default-src 'self' *"
                ]
                
                for pattern in unsafe_patterns:
                    self.assertNotIn(pattern, csp.lower(), 
                                   f"Unsafe CSP configuration found: {pattern} on {endpoint}")
                
                # Check that 'none' is used for unused features
                unused_features = [
                    'object-src',
                    'base-uri'
                ]
                
                for feature in unused_features:
                    if feature in csp:
                        directive_value = re.search(f"{feature} ([^;]+)", csp)
                        if directive_value:
                            self.assertIn("'none'", directive_value.group(1), 
                                         f"Unused feature {feature} should be set to 'none' on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_x_content_type_options(self):
        """Test for X-Content-Type-Options header set to nosniff"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertIn('X-Content-Type-Options', response.headers, 
                            f"Missing X-Content-Type-Options header on {endpoint}")
                
                self.assertEqual(response.headers['X-Content-Type-Options'].lower(), 'nosniff', 
                               f"X-Content-Type-Options should be set to 'nosniff' on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_x_frame_options(self):
        """Test for proper X-Frame-Options header"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertIn('X-Frame-Options', response.headers, 
                            f"Missing X-Frame-Options header on {endpoint}")
                
                valid_values = ['deny', 'sameorigin']
                value = response.headers['X-Frame-Options'].lower()
                
                self.assertIn(value, valid_values, 
                            f"X-Frame-Options should be set to DENY or SAMEORIGIN on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_strict_transport_security(self):
        """Test for proper Strict-Transport-Security (HSTS) header"""
        # Skip HSTS test for localhost/non-HTTPS connections
        if not self.base_url.startswith('https://'):
            return
            
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertIn('Strict-Transport-Security', response.headers, 
                            f"Missing HSTS header on {endpoint}")
                
                hsts = response.headers['Strict-Transport-Security']
                
                # Check for max-age of at least 180 days (15552000 seconds)
                max_age_match = re.search(r'max-age=(\d+)', hsts)
                self.assertIsNotNone(max_age_match, f"HSTS header missing max-age directive on {endpoint}")
                
                if max_age_match:
                    max_age = int(max_age_match.group(1))
                    self.assertGreaterEqual(max_age, 15552000, 
                                         f"HSTS max-age should be at least 180 days on {endpoint}")
                
                # Check for includeSubDomains directive
                self.assertIn('includesubdomains', hsts.lower(), 
                            f"HSTS header should include the includeSubDomains directive on {endpoint}")
                
                # Check for preload directive (recommended but not required)
                if 'preload' not in hsts.lower():
                    print(f"Warning: HSTS preload directive not found on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_referrer_policy(self):
        """Test for proper Referrer-Policy header"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertIn('Referrer-Policy', response.headers, 
                            f"Missing Referrer-Policy header on {endpoint}")
                
                secure_policies = [
                    'no-referrer', 
                    'no-referrer-when-downgrade', 
                    'same-origin',
                    'strict-origin', 
                    'strict-origin-when-cross-origin'
                ]
                
                value = response.headers['Referrer-Policy'].lower()
                
                self.assertIn(value, secure_policies, 
                            f"Referrer-Policy should use a secure policy on {endpoint}")
                
                # Check for insecure policies
                insecure_policies = ['unsafe-url', 'origin-when-cross-origin', 'origin']
                for policy in insecure_policies:
                    self.assertNotIn(policy, value, 
                                   f"Referrer-Policy uses insecure policy '{policy}' on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_permissions_policy(self):
        """Test for proper Permissions-Policy header"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                self.assertTrue(
                    'Permissions-Policy' in response.headers or 'Feature-Policy' in response.headers, 
                    f"Missing Permissions-Policy or Feature-Policy header on {endpoint}"
                )
                
                policy = response.headers.get('Permissions-Policy', 
                                            response.headers.get('Feature-Policy', ''))
                
                # Check that sensitive permissions are restricted
                sensitive_features = [
                    'geolocation', 
                    'microphone', 
                    'camera',
                    'payment',
                    'usb',
                    'bluetooth',
                    'midi'
                ]
                
                for feature in sensitive_features:
                    if feature in policy:
                        feature_value = re.search(f"{feature}=([^,]+)", policy)
                        if feature_value:
                            # Should not be allowed for all (*) origins
                            self.assertNotIn("*", feature_value.group(1), 
                                           f"Sensitive feature {feature} should not be allowed for all origins on {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_x_xss_protection(self):
        """Test for proper X-XSS-Protection header"""
        for endpoint in self.test_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers if 'protected' in endpoint else self.headers,
                    timeout=5
                )
                
                # While CSP makes X-XSS-Protection less necessary, it's still good to have
                if 'X-XSS-Protection' in response.headers:
                    value = response.headers['X-XSS-Protection']
                    
                    # Should be either "1; mode=block" or "0" (if using CSP instead)
                    self.assertTrue(
                        value == "1; mode=block" or value == "0", 
                        f"X-XSS-Protection should be set to '1; mode=block' or '0' on {endpoint}"
                    )
            except requests.RequestException:
                # Skip unreachable endpoints
                continue
    
    def test_cache_control_for_sensitive_pages(self):
        """Test for proper Cache-Control headers on sensitive pages"""
        sensitive_endpoints = [
            self.auth_url,
            self.protected_endpoint,
            f"{self.base_url}/api/v1/admin/dashboard",
            f"{self.base_url}/api/v1/user/settings",
            f"{self.base_url}/api/v1/payment/history",
        ]
        
        for endpoint in sensitive_endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=self.auth_headers,
                    timeout=5
                )
                
                self.assertIn('Cache-Control', response.headers, 
                            f"Missing Cache-Control header on sensitive endpoint {endpoint}")
                
                cache_control = response.headers['Cache-Control'].lower()
                
                # Sensitive pages should have strict caching controls
                required_directives = ['no-store', 'no-cache', 'private']
                
                for directive in required_directives:
                    self.assertIn(directive, cache_control, 
                                f"Cache-Control header should include '{directive}' on sensitive endpoint {endpoint}")
                
                # Should not have directives that allow caching
                forbidden_directives = ['public', 'max-age=', 's-maxage=']
                
                for directive in forbidden_directives:
                    self.assertNotIn(directive, cache_control, 
                                   f"Cache-Control header should not include '{directive}' on sensitive endpoint {endpoint}")
            except requests.RequestException:
                # Skip unreachable endpoints
                continue

if __name__ == "__main__":
    unittest.main()
