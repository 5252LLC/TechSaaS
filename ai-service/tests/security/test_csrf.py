"""
Cross-Site Request Forgery (CSRF) Protection Tests

This module tests protection against CSRF attacks in the TechSaaS platform.
It includes tests for:
- CSRF token implementation
- Token validation
- Same-origin policy enforcement
- Cookie protection mechanisms
"""

import unittest
import requests
import re
import json
import os
import sys
import html
import time
import random
import string
from urllib.parse import urlparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import project modules
from api.v1.utils.token_generator import generate_test_token

class CSRFSecurityTests(unittest.TestCase):
    """Test cases for CSRF protection"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.profile_url = f"{self.base_url}/api/v1/user/profile"
        self.password_change_url = f"{self.base_url}/api/v1/user/password"
        self.notes_url = f"{self.base_url}/api/v1/notes"
        
        # Test credentials
        self.user_credentials = {
            "email": "test@example.com",
            "password": "SecureP@ssw0rd!"
        }
        
        # Set up headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TechSaaS-Security-Test/1.0',
        }
        
        # Generate a unique identifier for test data
        self.test_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Login to get session information
        self.session = requests.Session()
        try:
            login_response = self.session.post(
                self.login_url, 
                headers=self.headers, 
                json=self.user_credentials,
                timeout=5
            )
            
            # Add JWT token to headers if available
            if login_response.status_code == 200:
                token = login_response.json().get('access_token')
                if token:
                    self.headers['Authorization'] = f"Bearer {token}"
                    self.session.headers.update({'Authorization': f"Bearer {token}"})
        except:
            # Continue without authentication if login fails
            pass
    
    def test_csrf_token_in_forms(self):
        """Test that forms include CSRF protection tokens"""
        # Get HTML pages that might contain forms
        html_endpoints = [
            f"{self.base_url}/",
            f"{self.base_url}/profile",
            f"{self.base_url}/settings",
            f"{self.base_url}/contact",
            f"{self.base_url}/password/reset"
        ]
        
        for endpoint in html_endpoints:
            try:
                response = self.session.get(endpoint, timeout=5)
                
                if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                    # Check for forms in the HTML
                    form_pattern = re.compile(r'<form[^>]*>.*?</form>', re.DOTALL)
                    forms = form_pattern.findall(response.text)
                    
                    for form in forms:
                        # Skip forms that don't submit data to the server (e.g., search forms)
                        if 'method="get"' in form.lower() or "method='get'" in form.lower():
                            continue
                            
                        # Check for CSRF token in the form
                        has_csrf_token = (
                            'csrf' in form.lower() or 
                            '_token' in form.lower() or
                            'xsrf' in form.lower()
                        )
                        
                        self.assertTrue(has_csrf_token, 
                                     f"Form found without CSRF protection at {endpoint}")
            except:
                # Skip unavailable endpoints
                continue
    
    def test_csrf_token_validation(self):
        """Test that CSRF tokens are validated on form submission"""
        # First, get a valid CSRF token
        csrf_token = self._get_csrf_token()
        
        if not csrf_token:
            print("Warning: Could not obtain CSRF token, skipping validation test")
            return
            
        # Test endpoints that should require CSRF protection
        state_changing_endpoints = [
            self.password_change_url,
            self.profile_url,
            f"{self.base_url}/api/v1/settings",
            f"{self.base_url}/api/v1/user/email"
        ]
        
        for endpoint in state_changing_endpoints:
            # Test with missing CSRF token
            no_token_response = self.session.post(
                endpoint, 
                headers=self.headers,
                json={"test_field": f"value-{self.test_id}"}
            )
            
            # Test with invalid CSRF token
            invalid_token_headers = self.headers.copy()
            invalid_token_headers['X-CSRF-TOKEN'] = 'invalid_token'
            
            invalid_token_response = self.session.post(
                endpoint, 
                headers=invalid_token_headers,
                json={"test_field": f"value-{self.test_id}"}
            )
            
            # Test with valid CSRF token
            valid_token_headers = self.headers.copy()
            valid_token_headers['X-CSRF-TOKEN'] = csrf_token
            
            valid_token_response = self.session.post(
                endpoint, 
                headers=valid_token_headers,
                json={"test_field": f"value-{self.test_id}"}
            )
            
            # At least one of the invalid approaches should fail if CSRF protection is implemented
            if valid_token_response.status_code in [200, 201, 204]:
                self.assertTrue(
                    no_token_response.status_code in [400, 401, 403] or 
                    invalid_token_response.status_code in [400, 401, 403],
                    f"CSRF protection may be bypassed at {endpoint}"
                )
    
    def test_csrf_protection_for_non_browser_clients(self):
        """Test that CSRF protection doesn't break API clients with proper tokens"""
        # Create a new session without browser cookies
        api_client = requests.Session()
        api_client.headers.update(self.headers)
        
        # Try to create a resource using API token authentication
        payload = {
            "title": f"CSRF Test Note {self.test_id}",
            "content": "This is a test note for CSRF testing."
        }
        
        response = api_client.post(self.notes_url, json=payload)
        
        # API clients with proper tokens should be able to create resources
        self.assertIn(response.status_code, [200, 201, 204], 
                    "CSRF protection incorrectly blocks legitimate API clients")
    
    def test_same_origin_policy_enforcement(self):
        """Test enforcement of same-origin policy for CSRF protection"""
        # Test with different origin headers
        other_origins = [
            "https://evil-site.com",
            "http://attacker.org",
            "https://fake-techsaas.com",
            "https://techsaas.tech.attacker.com"
        ]
        
        for origin in other_origins:
            # Create headers with different origin
            cross_origin_headers = self.headers.copy()
            cross_origin_headers['Origin'] = origin
            cross_origin_headers['Referer'] = f"{origin}/fake-page"
            
            # Try to make state-changing requests with cross-origin headers
            response = requests.post(
                self.profile_url, 
                headers=cross_origin_headers,
                json={"name": f"CSRF Test {self.test_id}"}
            )
            
            # Check SameSite cookie attribute in response
            if 'Set-Cookie' in response.headers:
                cookies = response.headers.get_all('Set-Cookie')
                
                for cookie in cookies:
                    if 'session' in cookie.lower() or 'csrf' in cookie.lower() or 'token' in cookie.lower():
                        self.assertTrue('samesite' in cookie.lower(), 
                                     f"Cookie missing SameSite attribute: {cookie}")
    
    def test_cookie_security_attributes(self):
        """Test that cookies have proper security attributes for CSRF protection"""
        # Get cookies from a fresh session
        response = requests.get(self.base_url)
        
        if 'Set-Cookie' in response.headers:
            cookies = response.headers.get_all('Set-Cookie')
            
            for cookie in cookies:
                # Skip non-security cookies like analytics
                if 'session' in cookie.lower() or 'csrf' in cookie.lower() or 'token' in cookie.lower():
                    # Check for SameSite attribute
                    self.assertTrue('samesite' in cookie.lower(), 
                                 f"Security cookie missing SameSite attribute: {cookie}")
                    
                    # Check for HttpOnly flag for session cookies
                    if 'session' in cookie.lower():
                        self.assertTrue('httponly' in cookie.lower(), 
                                     f"Session cookie missing HttpOnly flag: {cookie}")
                    
                    # Check for Secure flag (except for localhost testing)
                    if not self.base_url.startswith('http://localhost'):
                        self.assertTrue('secure' in cookie.lower(), 
                                     f"Security cookie missing Secure flag: {cookie}")
    
    def test_double_submit_cookie_pattern(self):
        """Test if double submit cookie pattern is implemented correctly"""
        # Get CSRF token from cookies
        response = self.session.get(f"{self.base_url}/api/v1/csrf-token")
        
        csrf_cookie = None
        for cookie in self.session.cookies:
            if 'csrf' in cookie.name.lower() or 'xsrf' in cookie.name.lower():
                csrf_cookie = cookie.value
                break
        
        if csrf_cookie:
            # If CSRF token is in cookies, test the double submit pattern
            headers = self.headers.copy()
            headers['X-CSRF-TOKEN'] = csrf_cookie
            
            # Make request with matching cookie and header token
            valid_response = self.session.post(
                self.profile_url, 
                headers=headers,
                json={"name": f"CSRF Test {self.test_id}"}
            )
            
            # Make request with mismatched token
            headers['X-CSRF-TOKEN'] = csrf_cookie + "_invalid"
            invalid_response = self.session.post(
                self.profile_url, 
                headers=headers,
                json={"name": f"CSRF Test Invalid {self.test_id}"}
            )
            
            # Valid request should succeed, invalid should fail
            if valid_response.status_code in [200, 201, 204]:
                self.assertNotIn(invalid_response.status_code, [200, 201, 204], 
                               "Double submit cookie pattern not properly validated")
    
    def _get_csrf_token(self):
        """Helper method to get a valid CSRF token"""
        # Try different approaches to get a CSRF token
        
        # 1. Check if there's a dedicated CSRF token endpoint
        try:
            response = self.session.get(f"{self.base_url}/api/v1/csrf-token")
            if response.status_code == 200:
                token = response.json().get('csrf_token', response.json().get('token'))
                if token:
                    return token
        except:
            pass
        
        # 2. Look for CSRF token in cookies
        for cookie in self.session.cookies:
            if 'csrf' in cookie.name.lower() or 'xsrf' in cookie.name.lower():
                return cookie.value
        
        # 3. Try to extract CSRF token from a form
        try:
            response = self.session.get(f"{self.base_url}/settings")
            if response.status_code == 200:
                # Look for CSRF token in form inputs
                csrf_pattern = re.compile(r'<input[^>]*name=["\'](csrf_token|_token|csrftoken|xsrf_token)["\'][^>]*value=["\'](.*?)["\']', re.IGNORECASE)
                match = csrf_pattern.search(response.text)
                if match:
                    return match.group(2)
        except:
            pass
        
        # No CSRF token found
        return None

if __name__ == "__main__":
    unittest.main()
