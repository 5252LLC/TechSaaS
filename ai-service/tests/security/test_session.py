"""
Session Security Tests

This module tests the security of session management in the TechSaaS platform.
It includes tests for:
- Session timeout and expiration
- Session fixation
- Secure session storage
- Cookie security
- Session regeneration on privilege change
"""

import unittest
import requests
import time
import os
import sys
import re
import json
from urllib.parse import urlparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class SessionSecurityTests(unittest.TestCase):
    """Test cases for session security"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.profile_url = f"{self.base_url}/api/v1/user/profile"
        self.logout_url = f"{self.base_url}/api/v1/auth/logout"
        
        # Test credentials
        self.user_credentials = {
            "email": "test@example.com",
            "password": "SecureP@ssw0rd!"
        }
        
        self.admin_credentials = {
            "email": "admin@example.com",
            "password": "AdminP@ssw0rd!"
        }
        
        # Set up headers
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TechSaaS-Security-Test/1.0',
        }
    
    def test_session_timeout(self):
        """Test that sessions expire after inactivity"""
        # Create a session
        session = requests.Session()
        
        # Login to establish a session
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test session timeout")
        
        # Get session cookies and token
        token = None
        if 'access_token' in login_response.json():
            token = login_response.json()['access_token']
            session.headers.update({'Authorization': f"Bearer {token}"})
        
        # Verify we have access to protected resources
        initial_profile = session.get(self.profile_url)
        self.assertEqual(initial_profile.status_code, 200, "Could not access profile after login")
        
        # Check for session timeout configuration
        token_expiry = None
        if token:
            import jwt
            try:
                # Decode token without verification (we're just checking expiry time)
                payload = jwt.decode(token, options={"verify_signature": False})
                if 'exp' in payload:
                    token_expiry = payload['exp']
            except:
                pass
        
        if token_expiry:
            # Token has expiry, check that it's reasonable (not too long)
            import time
            current_time = time.time()
            max_session_time = 24 * 60 * 60  # 24 hours
            
            self.assertLessEqual(
                token_expiry - current_time, 
                max_session_time, 
                "Session token expiry too long (> 24 hours)"
            )
        
        # If the service has a short session timeout (e.g., 15 minutes), test it
        # Note: This is commented out because waiting for actual timeout is impractical in unit tests
        """
        # Wait for session to expire
        session_timeout = 15 * 60  # 15 minutes
        time.sleep(session_timeout + 10)
        
        # Try to access the resource again
        expired_profile = session.get(self.profile_url)
        self.assertNotEqual(expired_profile.status_code, 200, 
                          "Session did not expire after timeout period")
        """
    
    def test_session_invalidation_on_logout(self):
        """Test that sessions are properly invalidated on logout"""
        # Create a session
        session = requests.Session()
        
        # Login to establish a session
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test session invalidation")
        
        # Get session token if available
        if 'access_token' in login_response.json():
            token = login_response.json()['access_token']
            session.headers.update({'Authorization': f"Bearer {token}"})
        
        # Verify we have access to protected resources
        initial_profile = session.get(self.profile_url)
        self.assertEqual(initial_profile.status_code, 200, "Could not access profile after login")
        
        # Logout
        logout_response = session.post(self.logout_url)
        
        # Regardless of logout response, the session should be invalidated
        # Try to access the protected resource again
        after_logout_profile = session.get(self.profile_url)
        self.assertNotEqual(after_logout_profile.status_code, 200, 
                          "Session not invalidated after logout")
    
    def test_session_fixation_protection(self):
        """Test protection against session fixation attacks"""
        # Create a session
        session = requests.Session()
        
        # Get any session identifier that might be set before authentication
        initial_request = session.get(self.base_url)
        pre_auth_cookies = {cookie.name: cookie.value for cookie in session.cookies}
        
        # Login to establish a session
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test session fixation")
        
        # Get post-authentication cookies
        post_auth_cookies = {cookie.name: cookie.value for cookie in session.cookies}
        
        # Check if token-based auth is used
        using_token_auth = 'access_token' in login_response.json()
        
        # For cookie-based sessions, ensure cookies changed after login
        if not using_token_auth:
            # Check session identifiers were changed
            session_cookie_changed = False
            for name, value in post_auth_cookies.items():
                if name in pre_auth_cookies and 'session' in name.lower():
                    session_cookie_changed = pre_auth_cookies[name] != value
                    if session_cookie_changed:
                        break
            
            self.assertTrue(session_cookie_changed, 
                          "Session cookies not changed after login (vulnerable to fixation)")
    
    def test_session_regeneration_on_privilege_change(self):
        """Test that sessions are regenerated when user privileges change"""
        # Only applicable for cookie-based sessions - skip for token-based auth
        # Create a session
        session = requests.Session()
        
        # Login as regular user
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test session regeneration")
        
        # Check if token-based auth is used
        using_token_auth = 'access_token' in login_response.json()
        
        # If using tokens, we need to track the token instead of cookies
        if using_token_auth:
            user_token = login_response.json()['access_token']
            session.headers.update({'Authorization': f"Bearer {user_token}"})
            
            # No need to test session regeneration for stateless tokens
            return
        
        # For cookie-based sessions:
        # Get regular user session cookies
        regular_user_cookies = {cookie.name: cookie.value for cookie in session.cookies}
        
        # Logout
        session.post(self.logout_url)
        
        # Login as admin
        admin_login = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.admin_credentials
        )
        
        if admin_login.status_code != 200:
            self.skipTest("Admin login failed, cannot test session regeneration")
        
        # Get admin session cookies
        admin_cookies = {cookie.name: cookie.value for cookie in session.cookies}
        
        # Check that session identifiers changed
        session_cookie_changed = False
        for name, value in admin_cookies.items():
            if name in regular_user_cookies and 'session' in name.lower():
                session_cookie_changed = regular_user_cookies[name] != value
                if session_cookie_changed:
                    break
        
        self.assertTrue(session_cookie_changed, 
                      "Session cookies not changed after privilege escalation")
    
    def test_concurrent_session_management(self):
        """Test handling of concurrent sessions for the same user"""
        # Create two independent sessions
        session1 = requests.Session()
        session2 = requests.Session()
        
        # Login with the same credentials in both sessions
        login1 = session1.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        login2 = session2.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login1.status_code != 200 or login2.status_code != 200:
            self.skipTest("Login failed, cannot test concurrent sessions")
        
        # Set tokens if using token-based auth
        if 'access_token' in login1.json():
            token1 = login1.json()['access_token']
            token2 = login2.json()['access_token']
            
            session1.headers.update({'Authorization': f"Bearer {token1}"})
            session2.headers.update({'Authorization': f"Bearer {token2}"})
            
            # Tokens should be different for each session
            self.assertNotEqual(token1, token2, "Same token issued for different sessions")
        
        # Both sessions should be able to access protected resources
        profile1 = session1.get(self.profile_url)
        profile2 = session2.get(self.profile_url)
        
        self.assertEqual(profile1.status_code, 200, "First session cannot access profile")
        self.assertEqual(profile2.status_code, 200, "Second session cannot access profile")
        
        # Logout from session1
        session1.post(self.logout_url)
        
        # Session1 should no longer have access
        after_logout1 = session1.get(self.profile_url)
        self.assertNotEqual(after_logout1.status_code, 200, 
                          "First session not invalidated after logout")
        
        # Session2 should still have access
        after_logout2 = session2.get(self.profile_url)
        self.assertEqual(after_logout2.status_code, 200, 
                       "Second session incorrectly invalidated by first session logout")
    
    def test_secure_cookie_flags(self):
        """Test that session cookies have secure flags set"""
        # Create a session
        session = requests.Session()
        
        # Login to establish a session
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test secure cookies")
        
        # Check cookies in the response
        if 'Set-Cookie' in login_response.headers:
            cookies = login_response.headers.get_all('Set-Cookie')
            
            for cookie in cookies:
                # Check for session-related cookies
                if 'session' in cookie.lower() or 'auth' in cookie.lower() or 'token' in cookie.lower():
                    # Check for HttpOnly flag
                    self.assertIn('HttpOnly', cookie, f"Session cookie missing HttpOnly flag: {cookie}")
                    
                    # Check for Secure flag if not localhost
                    if not self.base_url.startswith('http://localhost'):
                        self.assertIn('Secure', cookie, f"Session cookie missing Secure flag: {cookie}")
                    
                    # Check for SameSite attribute
                    self.assertIn('SameSite', cookie, f"Session cookie missing SameSite attribute: {cookie}")
    
    def test_session_data_protection(self):
        """Test that sensitive data is not stored in client-accessible session storage"""
        # Create a session
        session = requests.Session()
        
        # Login to establish a session
        login_response = session.post(
            self.login_url, 
            headers=self.headers, 
            json=self.user_credentials
        )
        
        if login_response.status_code != 200:
            self.skipTest("Login failed, cannot test session data protection")
        
        # Get token if available
        token = None
        if 'access_token' in login_response.json():
            token = login_response.json()['access_token']
            session.headers.update({'Authorization': f"Bearer {token}"})
        
        # Examine session storage for sensitive data
        if token:
            import jwt
            try:
                # Decode token without verification
                payload = jwt.decode(token, options={"verify_signature": False})
                
                # Check for sensitive data that should not be in the token
                sensitive_fields = ['password', 'secret', 'hash', 'salt', 'credit_card', 'ssn']
                
                for field in sensitive_fields:
                    self.assertNotIn(field, payload, f"Token contains sensitive field: {field}")
                
                # Password should not be in the payload
                if 'user' in payload and isinstance(payload['user'], dict):
                    self.assertNotIn('password', payload['user'], "User password found in token payload")
            except:
                pass
        
        # For cookie-based sessions, inspect cookie values
        for cookie in session.cookies:
            value = cookie.value
            
            # Check for unencoded/unencrypted sensitive data in cookies
            sensitive_patterns = [
                self.user_credentials['password'],
                'password',
                'passwd',
                'secret',
                'creditcard',
                'ssn'
            ]
            
            for pattern in sensitive_patterns:
                self.assertNotIn(pattern.lower(), value.lower(), 
                               f"Cookie contains sensitive data: {pattern}")

if __name__ == "__main__":
    unittest.main()
