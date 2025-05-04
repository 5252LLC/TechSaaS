"""
Authentication Security Tests

This module tests the security of the authentication system in the TechSaaS platform.
It includes tests for:
- Authentication bypass attempts
- Weak password policies
- Brute force protection
- Session fixation protection
- Credential exposure
"""

import unittest
import requests
import time
import json
import os
import sys
from urllib.parse import urlparse
import jwt
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import project modules
from api.v1.utils.config import JWT_SECRET_KEY, JWT_ALGORITHM
from api.v1.utils.token_generator import generate_test_token

class AuthenticationSecurityTests(unittest.TestCase):
    """Test cases for authentication security"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.protected_url = f"{self.base_url}/api/v1/protected/user-profile"
        
        # Test credentials
        self.valid_credentials = {
            "email": "test@example.com",
            "password": "SecureP@ssw0rd!"
        }
        
        # Create a valid token for testing
        self.valid_token = generate_test_token(
            user_id="test-user-123",
            email="test@example.com",
            role="user",
            tier="basic"
        )
        
        # Create an expired token for testing
        self.expired_token = generate_test_token(
            user_id="test-user-123",
            email="test@example.com",
            role="user",
            tier="basic",
            expires_in_minutes=-30  # Token expired 30 minutes ago
        )
        
        # Set up headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TechSaaS-Security-Test/1.0',
        }
    
    def test_auth_bypass_empty_token(self):
        """Test authentication bypass with empty token"""
        headers = self.headers.copy()
        # Send request without token
        response = requests.get(self.protected_url, headers=headers)
        
        # Should not allow access
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [401, 403])
    
    def test_auth_bypass_malformed_token(self):
        """Test authentication bypass with malformed token"""
        malformed_tokens = [
            "Bearer malformed",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", # Incomplete JWT
            "Bearer " + "A" * 100, # Random string
            "Basic " + self.valid_token, # Wrong scheme
        ]
        
        for token in malformed_tokens:
            headers = self.headers.copy()
            headers['Authorization'] = token
            
            response = requests.get(self.protected_url, headers=headers)
            
            # Should not allow access
            self.assertNotEqual(response.status_code, 200, f"Malformed token bypass: {token}")
            self.assertTrue(response.status_code in [401, 403])
    
    def test_auth_bypass_expired_token(self):
        """Test authentication bypass with expired token"""
        headers = self.headers.copy()
        headers['Authorization'] = f"Bearer {self.expired_token}"
        
        response = requests.get(self.protected_url, headers=headers)
        
        # Should not allow access
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [401, 403])
    
    def test_auth_bypass_tampered_token(self):
        """Test authentication bypass with tampered token"""
        # Decode valid token
        token_parts = self.valid_token.split('.')
        header = token_parts[0]
        
        # Create a tampered payload with admin role
        payload_json = json.loads(jwt.decode(self.valid_token, options={"verify_signature": False}))
        payload_json['role'] = 'admin'  # Attempt privilege escalation
        
        # Encode tampered payload
        tampered_payload = jwt.encode(payload_json, 'wrong_secret', algorithm=JWT_ALGORITHM).split('.')[1]
        
        # Reassemble token with original header and signature but tampered payload
        tampered_token = f"{header}.{tampered_payload}.{token_parts[2]}"
        
        headers = self.headers.copy()
        headers['Authorization'] = f"Bearer {tampered_token}"
        
        # Request a protected admin endpoint
        admin_url = f"{self.base_url}/api/v1/admin/dashboard"
        response = requests.get(admin_url, headers=headers)
        
        # Should not allow access
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [401, 403])
    
    def test_password_policy_weak_passwords(self):
        """Test rejection of weak passwords"""
        weak_passwords = [
            "password",
            "123456",
            "qwerty",
            "abc123",
            "letmein",
            self.valid_credentials["email"].split('@')[0],  # Username as password
        ]
        
        for password in weak_passwords:
            payload = {
                "email": "new_user@example.com",
                "password": password,
                "confirm_password": password
            }
            
            # Try to register with weak password
            register_url = f"{self.base_url}/api/v1/auth/register"
            response = requests.post(register_url, headers=self.headers, json=payload)
            
            # Should reject weak password
            self.assertNotEqual(response.status_code, 200)
            self.assertNotEqual(response.status_code, 201)
    
    def test_brute_force_protection(self):
        """Test protection against brute force attacks"""
        # Attempt multiple failed logins
        invalid_credentials = {
            "email": "test@example.com",
            "password": "WrongPassword123!"
        }
        
        # Track response times to detect rate limiting
        response_times = []
        status_codes = []
        
        for _ in range(10):
            start_time = time.time()
            response = requests.post(self.login_url, headers=self.headers, json=invalid_credentials)
            elapsed = time.time() - start_time
            
            response_times.append(elapsed)
            status_codes.append(response.status_code)
            
            # Add a small delay to avoid overwhelming the server
            time.sleep(0.5)
        
        # Check if later requests were rate limited or blocked
        self.assertTrue(
            # Either response time increased significantly
            response_times[-1] > response_times[0] * 1.5 or
            # Or requests were explicitly blocked
            status_codes[-1] in [429, 403],
            "Brute force protection not detected"
        )
    
    def test_session_fixation_protection(self):
        """Test protection against session fixation attacks"""
        # First, login to get a valid session
        login_response = requests.post(self.login_url, headers=self.headers, json=self.valid_credentials)
        
        if login_response.status_code == 200:
            # Extract authentication token
            auth_token = login_response.json().get('access_token')
            
            if auth_token:
                # Compare tokens before and after re-authentication
                auth_headers = self.headers.copy()
                auth_headers['Authorization'] = f"Bearer {auth_token}"
                
                # Re-authenticate
                reauth_response = requests.post(self.login_url, headers=auth_headers, json=self.valid_credentials)
                
                if reauth_response.status_code == 200:
                    new_token = reauth_response.json().get('access_token')
                    
                    # Tokens should be different to prevent session fixation
                    self.assertNotEqual(auth_token, new_token)
    
    def test_credentials_not_in_urls(self):
        """Test that credentials are not exposed in URLs"""
        # Check login with GET method (should not be allowed)
        login_with_get_url = f"{self.login_url}?email={self.valid_credentials['email']}&password={self.valid_credentials['password']}"
        response = requests.get(login_with_get_url)
        
        # Should not allow credentials in URL
        self.assertNotEqual(response.status_code, 200)
        
        # Check that the API doesn't return URLs with embedded credentials
        login_response = requests.post(self.login_url, headers=self.headers, json=self.valid_credentials)
        
        if login_response.status_code == 200:
            response_data = login_response.json()
            
            # Check all string values for URLs with credentials
            def check_for_credentials_in_urls(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        check_for_credentials_in_urls(value, f"{path}.{key}" if path else key)
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        check_for_credentials_in_urls(item, f"{path}[{i}]")
                elif isinstance(data, str) and "://" in data:
                    # Check if string is a URL
                    try:
                        parsed_url = urlparse(data)
                        # Check if URL contains password component
                        self.assertFalse('@' in parsed_url.netloc, 
                                        f"URL at {path} contains credentials: {data}")
                    except:
                        pass
                        
            check_for_credentials_in_urls(response_data)
    
    def test_secure_cookie_settings(self):
        """Test that authentication cookies use secure settings"""
        login_response = requests.post(self.login_url, headers=self.headers, json=self.valid_credentials)
        
        if login_response.status_code == 200 and 'Set-Cookie' in login_response.headers:
            cookies = login_response.headers.get_all('Set-Cookie')
            
            for cookie in cookies:
                # Check for HttpOnly flag
                self.assertTrue('HttpOnly' in cookie, f"Cookie missing HttpOnly flag: {cookie}")
                
                # Check for Secure flag if not localhost
                if not self.base_url.startswith('http://localhost'):
                    self.assertTrue('Secure' in cookie, f"Cookie missing Secure flag: {cookie}")
                
                # Check for SameSite attribute
                self.assertTrue('SameSite' in cookie, f"Cookie missing SameSite attribute: {cookie}")
    
    def test_additional_security_headers(self):
        """Test that security headers are set on authentication endpoints"""
        login_response = requests.post(self.login_url, headers=self.headers, json=self.valid_credentials)
        
        # List of important security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Content-Security-Policy',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        for header in security_headers:
            self.assertIn(header, login_response.headers, f"Missing security header: {header}")

if __name__ == "__main__":
    unittest.main()
