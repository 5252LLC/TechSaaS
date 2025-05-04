"""
API Key Management Tests

These tests verify the API key management functionality, including:
- Creation, validation, and revocation of API keys
- API key middleware for authentication
- Rate limiting functionality
- Integration with the audit trail for security and compliance
"""

import unittest
import json
from datetime import datetime, timedelta
import os
import tempfile
import uuid
import re

from api.v1.utils.api_key_manager import ApiKeyManager, init_api_key_schema
from api.v1.utils.audit_trail import AuditTrail, AuditEvent, get_audit_trail
from api.v1.middleware.authorization import generate_access_token

# Import the main app for testing
from app import create_app


class TestApiKeyManagement(unittest.TestCase):
    """Test cases for API key management functionality"""

    def setUp(self):
        """Set up test environment before each test case"""
        # Create a temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Create a test app with the temporary database
        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'AUDIT_DB_PATH': self.db_path,
            'SECRET_KEY': 'test_secret_key',
            'JWT_SECRET_KEY': 'test_jwt_secret',
            'AUDIT_SIGNING_KEY': 'test_audit_signing_key'
        })
        
        # Create a test client
        self.client = self.app.test_client()
        
        # Create test user data
        self.test_user = {
            'id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'SecurePassword123!',
            'roles': ['user'],
            'permissions': ['api_key_management']
        }
        
        # Create a test admin user
        self.admin_user = {
            'id': str(uuid.uuid4()),
            'email': 'admin@example.com',
            'username': 'adminuser',
            'password': 'AdminPassword123!',
            'roles': ['admin'],
            'permissions': ['api_key_management', 'admin']
        }
        
        # Initialize the database with test users
        with self.app.app_context():
            from api.v1.utils.database_util import get_db_connection
            from api.v1.utils.security_util import hash_password
            
            # Initialize database schema
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                roles TEXT,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
            ''')
            
            # Insert test user
            hashed_password = hash_password(self.test_user['password'])
            cursor.execute(
                '''
                INSERT INTO users (id, email, username, password_hash, roles, permissions)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    self.test_user['id'],
                    self.test_user['email'],
                    self.test_user['username'],
                    hashed_password,
                    ','.join(self.test_user['roles']),
                    ','.join(self.test_user['permissions'])
                )
            )
            
            # Insert admin user
            admin_hashed_password = hash_password(self.admin_user['password'])
            cursor.execute(
                '''
                INSERT INTO users (id, email, username, password_hash, roles, permissions)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    self.admin_user['id'],
                    self.admin_user['email'],
                    self.admin_user['username'],
                    admin_hashed_password,
                    ','.join(self.admin_user['roles']),
                    ','.join(self.admin_user['permissions'])
                )
            )
            
            # Initialize API key schema
            init_api_key_schema(conn)
            
            # Initialize audit trail tables
            audit_trail = AuditTrail()
            audit_trail.initialize_storage()
            
            conn.commit()
            
        # Generate test access tokens
        with self.app.app_context():
            self.test_token = generate_access_token(
                user_id=self.test_user['id'],
                email=self.test_user['email'],
                username=self.test_user['username'],
                roles=self.test_user['roles'],
                permissions=self.test_user['permissions']
            )
            
            self.admin_token = generate_access_token(
                user_id=self.admin_user['id'],
                email=self.admin_user['email'],
                username=self.admin_user['username'],
                roles=self.admin_user['roles'],
                permissions=self.admin_user['permissions']
            )
    
    def tearDown(self):
        """Clean up after each test case"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_create_api_key(self):
        """Test creating a new API key"""
        # Make request to create API key
        response = self.client.post(
            '/api/v1/apikeys/',
            headers={
                'Authorization': f'Bearer {self.test_token}',
                'Content-Type': 'application/json'
            },
            json={
                'name': 'Test API Key',
                'tier': 'basic',
                'scopes': ['read', 'write']
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 201)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('api_key', data['data'])
        self.assertIn('key_id', data['data'])
        
        # Validate API key format (tsk.uuid.secret)
        api_key = data['data']['api_key']
        self.assertTrue(api_key.startswith('tsk.'))
        self.assertEqual(len(api_key.split('.')), 3)
        
        # Store key ID for later tests
        self.api_key_id = data['data']['key_id']
        self.api_key = api_key
        
        # Verify audit trail entry
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the create event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=self.test_user['id'],
                action='create',
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, self.test_user['id'])
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, self.api_key_id)
            self.assertEqual(event.action, 'create')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_SUCCESS)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_HIGH)
            
            # Verify event details
            self.assertEqual(event.details['name'], 'Test API Key')
            self.assertEqual(event.details['tier'], 'basic')
            self.assertEqual(event.details['scopes'], ['read', 'write'])
    
    def test_list_api_keys(self):
        """Test listing API keys for a user"""
        # First create an API key
        self.test_create_api_key()
        
        # Make request to list API keys
        response = self.client.get(
            '/api/v1/apikeys/',
            headers={
                'Authorization': f'Bearer {self.test_token}'
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('api_keys', data['data'])
        
        # Verify we have at least one API key
        api_keys = data['data']['api_keys']
        self.assertGreaterEqual(len(api_keys), 1)
        
        # Verify the API key data
        api_key = next((k for k in api_keys if k['id'] == self.api_key_id), None)
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key['name'], 'Test API Key')
        self.assertEqual(api_key['tier'], 'basic')
        self.assertEqual(api_key['scopes'], ['read', 'write'])
        
        # Verify audit trail entry for listing keys
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the list event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=self.test_user['id'],
                action='list',
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, self.test_user['id'])
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, 'all')
            self.assertEqual(event.action, 'list')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_SUCCESS)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_MEDIUM)
            
            # Verify event details includes the count
            self.assertGreaterEqual(event.details['count'], 1)
    
    def test_verify_api_key(self):
        """Test verifying an API key"""
        # First create an API key
        self.test_create_api_key()
        
        # Make request to verify API key
        response = self.client.post(
            '/api/v1/apikeys/verify',
            headers={
                'X-API-Key': self.api_key
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('key_id', data['data'])
        self.assertEqual(data['data']['key_id'], self.api_key_id)
        
        # Verify audit trail entry for key validation
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the validate event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                resource_id=self.api_key_id,
                action='validate',
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, self.test_user['id'])
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, self.api_key_id)
            self.assertEqual(event.action, 'validate')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_SUCCESS)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_MEDIUM)
    
    def test_invalid_api_key(self):
        """Test using an invalid API key"""
        # Make request with invalid API key
        response = self.client.post(
            '/api/v1/apikeys/verify',
            headers={
                'X-API-Key': 'tsk.invalid-key.12345'
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 401)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid API key')
        
        # Verify audit trail entry for invalid key attempt
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the validate failure event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                action='validate',
                outcome=AuditEvent.OUTCOME_FAILURE,
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.action, 'validate')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_FAILURE)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_HIGH)
            self.assertEqual(event.details['reason'], 'invalid_key')
    
    def test_revoke_api_key(self):
        """Test revoking an API key"""
        # First create an API key
        self.test_create_api_key()
        
        # Make request to revoke API key
        response = self.client.delete(
            f'/api/v1/apikeys/{self.api_key_id}',
            headers={
                'Authorization': f'Bearer {self.test_token}'
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('message', data['data'])
        self.assertEqual(data['data']['message'], 'API key revoked successfully')
        
        # Verify the key no longer works
        verify_response = self.client.post(
            '/api/v1/apikeys/verify',
            headers={
                'X-API-Key': self.api_key
            }
        )
        
        # Assert response shows key is invalid
        self.assertEqual(verify_response.status_code, 401)
        
        # Verify audit trail entries for revocation
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the revoke event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=self.test_user['id'],
                action='revoke',
                resource_id=self.api_key_id,
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, self.test_user['id'])
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, self.api_key_id)
            self.assertEqual(event.action, 'revoke')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_SUCCESS)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_HIGH)
    
    def test_unauthorized_revoke(self):
        """Test trying to revoke another user's API key"""
        # First create an API key as the test user
        self.test_create_api_key()
        
        # Create another user
        other_user_id = str(uuid.uuid4())
        other_user_token = None
        
        with self.app.app_context():
            from api.v1.utils.database_util import get_db_connection
            from api.v1.utils.security_util import hash_password
            
            # Create the other user
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                '''
                INSERT INTO users (id, email, username, password_hash, roles, permissions)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    other_user_id,
                    'other@example.com',
                    'otheruser',
                    hash_password('OtherPassword123!'),
                    'user',
                    'api_key_management'
                )
            )
            
            conn.commit()
            
            # Generate token for other user
            other_user_token = generate_access_token(
                user_id=other_user_id,
                email='other@example.com',
                username='otheruser',
                roles=['user'],
                permissions=['api_key_management']
            )
        
        # Try to revoke the key as the other user
        response = self.client.delete(
            f'/api/v1/apikeys/{self.api_key_id}',
            headers={
                'Authorization': f'Bearer {other_user_token}'
            }
        )
        
        # Assert response shows unauthorized
        self.assertEqual(response.status_code, 404)
        
        # Verify audit trail entry for unauthorized revocation
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the revoke failure event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=other_user_id,
                action='revoke',
                outcome=AuditEvent.OUTCOME_FAILURE,
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, other_user_id)
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, self.api_key_id)
            self.assertEqual(event.action, 'revoke')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_FAILURE)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_HIGH)
            self.assertEqual(event.details['reason'], 'unauthorized')
    
    def test_admin_api_key_info(self):
        """Test admin access to detailed API key information"""
        # First create an API key as the test user
        self.test_create_api_key()
        
        # Make request to get API key info as admin
        response = self.client.get(
            f'/api/v1/apikeys/info/{self.api_key_id}',
            headers={
                'Authorization': f'Bearer {self.admin_token}'
            }
        )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        
        # Parse response data
        data = json.loads(response.data)
        self.assertIn('key_info', data['data'])
        self.assertIn('usage_stats', data['data'])
        
        # Verify the API key data
        key_info = data['data']['key_info']
        self.assertEqual(key_info['id'], self.api_key_id)
        self.assertEqual(key_info['user_id'], self.test_user['id'])
        self.assertEqual(key_info['name'], 'Test API Key')
        
        # Verify audit trail entry for admin info access
        with self.app.app_context():
            audit_trail = get_audit_trail()
            
            # Query for the info event
            events = audit_trail.query_events(
                event_type=AuditEvent.API_KEY_MANAGEMENT,
                actor_id=self.admin_user['id'],
                action='info',
                resource_id=self.api_key_id,
                limit=1
            )
            
            # Assert that we found the event
            self.assertEqual(len(events), 1)
            
            # Verify event details
            event = events[0]
            self.assertEqual(event.event_type, AuditEvent.API_KEY_MANAGEMENT)
            self.assertEqual(event.actor_id, self.admin_user['id'])
            self.assertEqual(event.resource_type, 'api_key')
            self.assertEqual(event.resource_id, self.api_key_id)
            self.assertEqual(event.action, 'info')
            self.assertEqual(event.outcome, AuditEvent.OUTCOME_SUCCESS)
            self.assertEqual(event.sensitivity, AuditEvent.SENSITIVITY_HIGH)
            self.assertEqual(event.details['key_owner'], self.test_user['id'])


if __name__ == '__main__':
    unittest.main()
