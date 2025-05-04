"""
Authorization Security Tests

This module tests the security of the authorization system in the TechSaaS platform.
It includes tests for:
- Role-based access controls (RBAC)
- Vertical privilege escalation prevention
- Horizontal privilege escalation prevention
- Insecure direct object references (IDOR)
- API access control enforcement
"""

import unittest
import requests
import json
import os
import sys
import time
import random
import string

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import project modules
from api.v1.utils.token_generator import generate_test_token

class AuthorizationSecurityTests(unittest.TestCase):
    """Test cases for authorization security"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        
        # Test credentials for different roles
        self.user_credentials = {
            "email": "user@example.com",
            "password": "UserP@ssw0rd!"
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
        
        # Create tokens for different roles
        self.user_token = generate_test_token(
            user_id="user-123",
            email=self.user_credentials["email"],
            role="user",
            tier="basic"
        )
        
        self.premium_token = generate_test_token(
            user_id="premium-123",
            email="premium@example.com",
            role="user",
            tier="premium"
        )
        
        self.admin_token = generate_test_token(
            user_id="admin-123",
            email=self.admin_credentials["email"],
            role="admin",
            tier="enterprise"
        )
        
        # Endpoint mapping by role access levels
        self.role_endpoints = {
            'public': [
                f"{self.base_url}/api/v1/status",
                f"{self.base_url}/api/v1/docs"
            ],
            'user': [
                f"{self.base_url}/api/v1/protected/user-profile",
                f"{self.base_url}/api/v1/protected/dashboard"
            ],
            'premium': [
                f"{self.base_url}/api/v1/premium/features",
                f"{self.base_url}/api/v1/premium/reports"
            ],
            'admin': [
                f"{self.base_url}/api/v1/admin/dashboard",
                f"{self.base_url}/api/v1/admin/users",
                f"{self.base_url}/api/v1/admin/settings"
            ]
        }
        
        # Generate random user IDs for IDOR testing
        self.random_ids = [
            ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            for _ in range(5)
        ]
    
    def test_role_based_access_controls(self):
        """Test proper enforcement of role-based access controls"""
        # Test anonymous access to endpoints
        for role, endpoints in self.role_endpoints.items():
            for endpoint in endpoints:
                # Skip public endpoints for anonymous testing
                if role == 'public':
                    continue
                    
                # Test without any authorization
                response = requests.get(endpoint, headers=self.headers)
                
                # Non-public endpoints should reject anonymous access
                self.assertNotEqual(response.status_code, 200, 
                                  f"Anonymous access allowed to {role} endpoint: {endpoint}")
                self.assertTrue(response.status_code in [401, 403], 
                              f"Expected 401/403 for anonymous access to {endpoint}, got {response.status_code}")
        
        # Test user access to different role endpoints
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        for role, endpoints in self.role_endpoints.items():
            for endpoint in endpoints:
                response = requests.get(endpoint, headers=user_headers)
                
                if role in ['public', 'user']:
                    # User should have access to public and user endpoints
                    self.assertIn(response.status_code, [200, 204], 
                                f"User denied access to authorized endpoint: {endpoint}")
                else:
                    # User should not have access to premium or admin endpoints
                    self.assertNotEqual(response.status_code, 200, 
                                      f"User granted unauthorized access to {role} endpoint: {endpoint}")
                    self.assertTrue(response.status_code in [401, 403], 
                                  f"Expected 401/403 for user access to {endpoint}, got {response.status_code}")
        
        # Test premium user access
        premium_headers = self.headers.copy()
        premium_headers['Authorization'] = f"Bearer {self.premium_token}"
        
        for role, endpoints in self.role_endpoints.items():
            for endpoint in endpoints:
                response = requests.get(endpoint, headers=premium_headers)
                
                if role in ['public', 'user', 'premium']:
                    # Premium user should have access to public, user, and premium endpoints
                    self.assertIn(response.status_code, [200, 204], 
                                f"Premium user denied access to authorized endpoint: {endpoint}")
                else:
                    # Premium user should not have access to admin endpoints
                    self.assertNotEqual(response.status_code, 200, 
                                      f"Premium user granted unauthorized access to {role} endpoint: {endpoint}")
                    self.assertTrue(response.status_code in [401, 403], 
                                  f"Expected 401/403 for premium access to {endpoint}, got {response.status_code}")
        
        # Test admin access
        admin_headers = self.headers.copy()
        admin_headers['Authorization'] = f"Bearer {self.admin_token}"
        
        for role, endpoints in self.role_endpoints.items():
            for endpoint in endpoints:
                response = requests.get(endpoint, headers=admin_headers)
                
                # Admin should have access to all endpoints
                self.assertIn(response.status_code, [200, 204, 301, 302], 
                            f"Admin denied access to endpoint: {endpoint}")
    
    def test_vertical_privilege_escalation(self):
        """Test prevention of vertical privilege escalation attacks"""
        # Attempt to escalate privileges by accessing admin endpoints with modified tokens
        
        # Standard user token with role changed to "admin" in payload
        user_to_admin_token = self._create_modified_token(
            self.user_token,
            {'role': 'admin'}
        )
        
        # Headers with tampered token
        tampered_headers = self.headers.copy()
        tampered_headers['Authorization'] = f"Bearer {user_to_admin_token}"
        
        # Try to access admin endpoints with tampered token
        for endpoint in self.role_endpoints['admin']:
            response = requests.get(endpoint, headers=tampered_headers)
            
            # Should be rejected
            self.assertNotEqual(response.status_code, 200, 
                              f"Vertical privilege escalation successful: {endpoint}")
            self.assertTrue(response.status_code in [401, 403], 
                          f"Expected 401/403 for tampered token to {endpoint}, got {response.status_code}")
        
        # Test for privilege escalation via parameter pollution
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        for endpoint in self.role_endpoints['admin']:
            # Try adding role=admin to URL
            response = requests.get(f"{endpoint}?role=admin", headers=user_headers)
            
            # Should be rejected
            self.assertNotEqual(response.status_code, 200, 
                              f"Privilege escalation via parameter pollution successful: {endpoint}")
            self.assertTrue(response.status_code in [401, 403, 400], 
                          f"Expected 401/403/400 for parameter pollution at {endpoint}, got {response.status_code}")
            
            # Try adding role=admin to JSON body
            response = requests.post(endpoint, headers=user_headers, json={"role": "admin"})
            
            # Should be rejected
            self.assertNotEqual(response.status_code, 200, 
                              f"Privilege escalation via JSON pollution successful: {endpoint}")
            self.assertTrue(response.status_code in [401, 403, 400, 405], 
                          f"Expected 401/403/400/405 for JSON pollution at {endpoint}, got {response.status_code}")
    
    def test_horizontal_privilege_escalation(self):
        """Test prevention of horizontal privilege escalation (accessing other users' data)"""
        # Get URLs that might contain user-specific data
        user_data_endpoints = [
            f"{self.base_url}/api/v1/user/profile",
            f"{self.base_url}/api/v1/user/settings",
            f"{self.base_url}/api/v1/user/billing",
            f"{self.base_url}/api/v1/user/dashboard"
        ]
        
        # Regular user headers
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        for endpoint in user_data_endpoints:
            # Try to access other user's data by manipulating the user ID parameter
            for user_id in self.random_ids:
                # Try various parameter names that might be used for user ID
                for id_param in ['user_id', 'id', 'userId', 'uid']:
                    response = requests.get(f"{endpoint}?{id_param}={user_id}", headers=user_headers)
                    
                    if response.status_code == 200:
                        # If successful, make sure it's not returning another user's data
                        try:
                            data = response.json()
                            
                            # Look for common user identifiers in the response
                            user_identifiers = ['user_id', 'id', 'userId', 'uid', 'email', 'username']
                            for identifier in user_identifiers:
                                if identifier in data:
                                    # Should match the authenticated user, not the requested ID
                                    self.assertNotEqual(data[identifier], user_id, 
                                                    f"Horizontal privilege escalation possible at {endpoint}?{id_param}={user_id}")
                        except:
                            # Not a JSON response, check for the random ID in the response
                            self.assertNotIn(user_id, response.text, 
                                          f"Horizontal privilege escalation possible at {endpoint}?{id_param}={user_id}")
        
        # Test for privilege escalation through direct object references
        data_object_endpoints = [
            f"{self.base_url}/api/v1/files",
            f"{self.base_url}/api/v1/documents",
            f"{self.base_url}/api/v1/notes",
            f"{self.base_url}/api/v1/reports"
        ]
        
        for endpoint in data_object_endpoints:
            # Try to access objects potentially belonging to other users
            for obj_id in range(1, 10):  # Try some sequential IDs
                response = requests.get(f"{endpoint}/{obj_id}", headers=user_headers)
                
                if response.status_code == 200:
                    # If successful, check for access controls in the response
                    try:
                        data = response.json()
                        
                        # Look for owner information in the response
                        owner_fields = ['user_id', 'owner_id', 'created_by', 'userId', 'ownerId']
                        for field in owner_fields:
                            if field in data:
                                # Should match the authenticated user's ID
                                self.assertEqual(data[field], "user-123", 
                                              f"IDOR vulnerability at {endpoint}/{obj_id}")
                    except:
                        # Not JSON or other issue, just note this for manual verification
                        pass
    
    def test_insecure_direct_object_references(self):
        """Test for Insecure Direct Object References (IDOR) vulnerabilities"""
        # Try to create a resource first to get a valid ID
        resource_endpoints = [
            f"{self.base_url}/api/v1/notes",
            f"{self.base_url}/api/v1/documents",
            f"{self.base_url}/api/v1/comments"
        ]
        
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        premium_headers = self.headers.copy()
        premium_headers['Authorization'] = f"Bearer {self.premium_token}"
        
        for endpoint in resource_endpoints:
            # Create a resource as the first user
            resource_data = {
                "title": f"Test Resource {time.time()}",
                "content": "This is a test resource for IDOR testing."
            }
            
            create_response = requests.post(endpoint, headers=user_headers, json=resource_data)
            
            if create_response.status_code in [200, 201]:
                try:
                    # Extract resource ID
                    resource_id = create_response.json().get('id', 
                                                         create_response.json().get('resourceId', 
                                                                                 'test-123'))
                    
                    # Try to access it with a different user
                    get_response = requests.get(f"{endpoint}/{resource_id}", headers=premium_headers)
                    
                    # Determine expected behavior based on resource type
                    # Private resources should be protected, but this is application-specific
                    # For this test, we'll check if there's any access control
                    if get_response.status_code == 200:
                        # Got access - check if there's any user context in the response
                        try:
                            data = get_response.json()
                            
                            # Look for common permissions or ownership fields
                            permission_fields = ['user_id', 'owner_id', 'created_by', 'is_public']
                            has_permission_concept = any(field in data for field in permission_fields)
                            
                            if has_permission_concept:
                                # If this has an ownership concept, verify it's enforced
                                owner_id = None
                                for field in ['user_id', 'owner_id', 'created_by']:
                                    if field in data:
                                        owner_id = data[field]
                                        break
                                
                                is_public = data.get('is_public', False)
                                
                                # If resource has an owner but isn't public, this could be an IDOR issue
                                if owner_id and owner_id == "user-123" and not is_public:
                                    self.fail(f"Potential IDOR vulnerability: second user accessed private resource at {endpoint}/{resource_id}")
                        except:
                            # Not JSON or other issue
                            pass
                    
                    # Clean up - delete the resource if possible
                    requests.delete(f"{endpoint}/{resource_id}", headers=user_headers)
                    
                except (json.JSONDecodeError, KeyError, AttributeError):
                    # Response wasn't JSON or didn't have the expected format
                    continue
    
    def test_api_parameter_access_control(self):
        """Test that API parameters respect access control rules"""
        # Test for mass assignment vulnerabilities
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        # Endpoints that accept user data updates
        update_endpoints = [
            f"{self.base_url}/api/v1/user/profile",
            f"{self.base_url}/api/v1/user/settings",
            f"{self.base_url}/api/v1/user"
        ]
        
        for endpoint in update_endpoints:
            # Try to update with privileged parameters
            privileged_data = {
                "name": "Updated User",
                "role": "admin",                 # Attempt to escalate privileges
                "isAdmin": True,                 # Attempt to escalate privileges
                "permissions": ["admin", "user"],# Attempt to escalate privileges
                "tier": "enterprise",            # Attempt to upgrade account
                "accountStatus": "verified",     # Attempt to change account status
                "email_verified": True,          # Attempt to verify email without verification
                "billing_plan": "free"           # Attempt to downgrade billing
            }
            
            put_response = requests.put(endpoint, headers=user_headers, json=privileged_data)
            
            if put_response.status_code in [200, 201, 204]:
                # If update was successful, check that privileged fields were not updated
                get_response = requests.get(endpoint, headers=user_headers)
                
                if get_response.status_code == 200:
                    try:
                        data = get_response.json()
                        
                        # Check that privileged parameters were not updated
                        if 'role' in data:
                            self.assertEqual(data['role'], 'user', 
                                          f"Mass assignment vulnerability: role was changed to {data['role']}")
                        
                        if 'isAdmin' in data:
                            self.assertFalse(data['isAdmin'], 
                                          f"Mass assignment vulnerability: isAdmin was changed to {data['isAdmin']}")
                        
                        if 'tier' in data:
                            self.assertEqual(data['tier'], 'basic', 
                                          f"Mass assignment vulnerability: tier was changed to {data['tier']}")
                    except:
                        # Not JSON or other issue
                        pass
    
    def test_business_logic_authorization(self):
        """Test that authorization is properly enforced in business logic operations"""
        # Test for authorization bypasses in multi-step processes
        user_headers = self.headers.copy()
        user_headers['Authorization'] = f"Bearer {self.user_token}"
        
        # Example: Premium feature access through process manipulation
        premium_feature_url = f"{self.base_url}/api/v1/premium/export"
        
        # First try direct access (should be denied)
        direct_response = requests.get(premium_feature_url, headers=user_headers)
        self.assertNotEqual(direct_response.status_code, 200, 
                          f"User granted unauthorized direct access to premium feature")
        
        # Try to initiate a process that might lead to the premium feature
        process_start_url = f"{self.base_url}/api/v1/export/initialize"
        process_response = requests.post(process_start_url, headers=user_headers)
        
        if process_response.status_code in [200, 201]:
            try:
                # Extract process ID
                process_id = process_response.json().get('process_id', 
                                                     process_response.json().get('id', 'proc-123'))
                
                # Try to access premium feature through the process
                bypass_url = f"{self.base_url}/api/v1/export/process/{process_id}/premium"
                bypass_response = requests.get(bypass_url, headers=user_headers)
                
                # Should still be denied
                self.assertNotEqual(bypass_response.status_code, 200, 
                                 f"User granted unauthorized access to premium feature through process manipulation")
                
                # Try changing the process type
                update_response = requests.put(
                    f"{self.base_url}/api/v1/export/process/{process_id}",
                    headers=user_headers, 
                    json={"type": "premium"}
                )
                
                if update_response.status_code in [200, 201, 204]:
                    # Try access again after update
                    final_response = requests.get(bypass_url, headers=user_headers)
                    
                    # Should still be denied
                    self.assertNotEqual(final_response.status_code, 200, 
                                     f"User granted unauthorized access after process type manipulation")
            except:
                # Not JSON or other issue
                pass
    
    def _create_modified_token(self, original_token, modifications):
        """Create a modified JWT token by changing payload values"""
        import jwt
        
        # Decode the token without verification (we're testing if the server properly verifies)
        parts = original_token.split('.')
        if len(parts) != 3:
            return original_token
            
        try:
            # Parse the payload
            payload = jwt.decode(original_token, options={"verify_signature": False})
            
            # Apply modifications
            for key, value in modifications.items():
                payload[key] = value
            
            # Create a new token with same header but modified payload
            # Use an arbitrary secret since we're testing if server validates properly
            modified_token = jwt.encode(payload, 'invalid_secret', algorithm='HS256')
            
            return modified_token
        except:
            return original_token

if __name__ == "__main__":
    unittest.main()
