"""
Token Security Tests

Tests the security of JWT token verification and authorization mechanisms
to confirm that authentication bypass vulnerabilities have been addressed.
"""

import unittest
import jwt
import json
import sys
import os
import time
from datetime import datetime, timedelta, timezone, UTC

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import the verification functions
from api.v1.middleware.authorization import verify_jwt_token, ROLE_HIERARCHY, token_blacklist
from api.v1.utils.config import JWT_SECRET_KEY, JWT_ALGORITHM

class TokenSecurityTests(unittest.TestCase):
    """Test cases for token security"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear token blacklist between tests
        token_blacklist.clear()
        
        # Create a valid token payload
        self.valid_payload = {
            'sub': 'user-123',
            'email': 'test@example.com',
            'role': 'user',
            'tier': 'basic',
            'iat': datetime.now(UTC),
            'exp': datetime.now(UTC) + timedelta(minutes=30),
            'type': 'access',
            'jti': 'test-jwt-id-123'
        }
        
        # Create a valid token
        self.valid_token = jwt.encode(
            self.valid_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
    
    def test_valid_token_verification(self):
        """Test that a valid token is properly verified"""
        result = verify_jwt_token(self.valid_token)
        self.assertIsNotNone(result, "Valid token was rejected")
        self.assertEqual(result['sub'], 'user-123', "Token payload was not correctly decoded")
    
    def test_invalid_token_format(self):
        """Test that tokens with invalid format are rejected"""
        # Test token with missing parts
        invalid_format = "header.payload"
        result = verify_jwt_token(invalid_format)
        self.assertIsNone(result, "Invalid format token was accepted")
        
        # Test non-string token
        result = verify_jwt_token(None)
        self.assertIsNone(result, "None token was accepted")
        
        result = verify_jwt_token(123)
        self.assertIsNone(result, "Numeric token was accepted")
    
    def test_expired_token(self):
        """Test that expired tokens are rejected"""
        expired_payload = self.valid_payload.copy()
        expired_payload['exp'] = datetime.now(UTC) - timedelta(minutes=10)
        
        expired_token = jwt.encode(
            expired_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(expired_token)
        self.assertIsNone(result, "Expired token was accepted")
    
    def test_invalid_signature(self):
        """Test that tokens with invalid signatures are rejected"""
        # Create token with different key
        invalid_signature_token = jwt.encode(
            self.valid_payload,
            'wrong-secret-key',
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(invalid_signature_token)
        self.assertIsNone(result, "Token with invalid signature was accepted")
    
    def test_missing_required_claims(self):
        """Test that tokens with missing required claims are rejected"""
        # Test missing 'type' claim
        missing_type_payload = self.valid_payload.copy()
        del missing_type_payload['type']
        
        missing_type_token = jwt.encode(
            missing_type_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(missing_type_token)
        self.assertIsNone(result, "Token with missing 'type' claim was accepted")
        
        # Test missing 'role' claim (required for access tokens)
        missing_role_payload = self.valid_payload.copy()
        del missing_role_payload['role']
        
        missing_role_token = jwt.encode(
            missing_role_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(missing_role_token)
        self.assertIsNone(result, "Token with missing 'role' claim was accepted")
    
    def test_wrong_token_type(self):
        """Test that tokens with incorrect type are rejected"""
        # Create refresh token
        refresh_payload = self.valid_payload.copy()
        refresh_payload['type'] = 'refresh'
        
        refresh_token = jwt.encode(
            refresh_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        # Verify as access token
        result = verify_jwt_token(refresh_token, required_type='access')
        self.assertIsNone(result, "Token with wrong type was accepted")
    
    def test_invalid_role(self):
        """Test that tokens with invalid roles are rejected"""
        # Create token with invalid role
        invalid_role_payload = self.valid_payload.copy()
        invalid_role_payload['role'] = 'nonexistent-role'
        
        invalid_role_token = jwt.encode(
            invalid_role_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(invalid_role_token)
        self.assertIsNone(result, "Token with invalid role was accepted")
    
    def test_blacklisted_token(self):
        """Test that blacklisted tokens are rejected"""
        # Add token to blacklist
        token_blacklist.add(self.valid_token)
        
        result = verify_jwt_token(self.valid_token)
        self.assertIsNone(result, "Blacklisted token was accepted")
    
    def test_blacklisted_jti(self):
        """Test that tokens with blacklisted JTI are rejected"""
        # Add JTI to blacklist
        token_blacklist.add(self.valid_payload['jti'])
        
        # Need to create a new token with the same JTI
        new_token = jwt.encode(
            self.valid_payload,
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        
        # The new token should be rejected because its JTI is blacklisted
        result = verify_jwt_token(new_token)
        self.assertIsNone(result, "Token with blacklisted JTI was accepted")
    
    def test_tampered_role_escalation(self):
        """Test that tokens with tampered roles for privilege escalation are rejected"""
        # Create admin token with the wrong signature
        admin_payload = self.valid_payload.copy()
        admin_payload['role'] = 'admin'
        
        # Encode with a wrong key (simulating a tampered token)
        tampered_token = jwt.encode(
            admin_payload,
            'fake-secret-for-tampering',
            algorithm=JWT_ALGORITHM
        )
        
        result = verify_jwt_token(tampered_token)
        self.assertIsNone(result, "Tampered token for privilege escalation was accepted")

if __name__ == '__main__':
    unittest.main()
