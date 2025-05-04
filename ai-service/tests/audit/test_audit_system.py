"""
System-level tests for the Audit Trail functionality.

This module tests the entire audit trail system using a complete
Flask application environment with database integration.
"""

import os
import sys
import unittest
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.sql import text

# Add the parent directory to path to import the application modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, parent_dir)

from complete_test_app import create_test_app
from api.v1.utils.audit_trail import AuditEvent 
from api.v1.models.base import db
from api.v1.models.audit import AuditEvent as DbAuditEvent


class TestAuditTrailSystem(unittest.TestCase):
    """System-level test cases for the audit trail system."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create the Flask app - Use file-based SQLite instead of in-memory for this test
        cls.test_db_path = os.path.join(os.path.dirname(__file__), 'test_audit.db')
        
        # Remove test database if it exists
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
            
        # Create the app with file-based SQLite
        cls.app = create_test_app()
        cls.app.config['TESTING'] = True
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{cls.test_db_path}'
        
        # Create app context and push it
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Create database tables - the SQLAlchemy instance is already registered by create_test_app()
        db.create_all()
        
        # Verify that the tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print("Tables created:", tables)
        
        # Create test client
        cls.client = cls.app.test_client()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Clean up database
        cls.app_context.pop()
        
        # Remove test database file
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except:
                print(f"Warning: Could not remove test database file {cls.test_db_path}")

    def setUp(self):
        """Set up before each test."""
        # Clear audit events table
        try:
            db.session.execute(text("DELETE FROM audit_events"))
            db.session.commit()
        except Exception as e:
            print(f"Error clearing audit_events table: {str(e)}")
            db.session.rollback()

    def test_authentication_audit(self):
        """Test auditing of authentication events."""
        # Make a login request
        response = self.client.post(
            '/api/test/auth/login',
            json={'user_id': 'test_user', 'success': True},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Check that an audit event was created
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        
        self.assertEqual(data['status'], 'success')
        events = data['data']['events']
        
        # Find the authentication event
        auth_events = [e for e in events 
                      if e['event_type'] == AuditEvent.USER_AUTHENTICATION 
                      and e['action'] == 'login']
        
        self.assertTrue(len(auth_events) > 0)
        auth_event = auth_events[0]
        
        self.assertEqual(auth_event['actor_id'], 'test_user')
        self.assertEqual(auth_event['outcome'], AuditEvent.OUTCOME_SUCCESS)

    def test_data_access_audit(self):
        """Test auditing of data access events."""
        # Make a data access request
        resource_type = 'document'
        resource_id = 'doc123'
        
        response = self.client.get(f'/api/test/data/{resource_type}/{resource_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Check that an audit event was created
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        
        self.assertEqual(data['status'], 'success')
        events = data['data']['events']
        
        # Find the data access event
        access_events = [e for e in events 
                        if e['event_type'] == AuditEvent.DATA_ACCESS 
                        and e['resource_id'] == resource_id]
        
        self.assertTrue(len(access_events) > 0)
        access_event = access_events[0]
        
        self.assertEqual(access_event['actor_id'], 'test_user')
        self.assertEqual(access_event['resource_type'], resource_type)
        self.assertEqual(access_event['details']['view_mode'], 'read_only')

    def test_data_modification_audit(self):
        """Test auditing of data modification events."""
        # Make a data modification request
        resource_type = 'settings'
        resource_id = 'user_settings_123'
        changes = {'theme': 'dark', 'notifications': 'enabled'}
        
        response = self.client.put(
            f'/api/test/data/{resource_type}/{resource_id}',
            json={'changes': changes},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Check that an audit event was created
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        
        self.assertEqual(data['status'], 'success')
        events = data['data']['events']
        
        # Find the data modification event
        mod_events = [e for e in events 
                      if e['event_type'] == AuditEvent.DATA_MODIFICATION 
                      and e['resource_id'] == resource_id]
        
        self.assertTrue(len(mod_events) > 0)
        mod_event = mod_events[0]
        
        self.assertEqual(mod_event['actor_id'], 'test_user')
        self.assertEqual(mod_event['resource_type'], resource_type)
        self.assertEqual(mod_event['action'], 'update')
        self.assertEqual(mod_event['details']['changes'], changes)

    def test_security_event_audit(self):
        """Test auditing of security events."""
        # Create a security event
        event_name = 'suspicious_login'
        severity = 'high'
        details = {'source_ip': '192.168.1.100', 'attempts': 5}
        
        response = self.client.post(
            '/api/test/security-event',
            json={
                'event_name': event_name,
                'severity': severity,
                'details': details
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Check that an audit event was created
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        
        self.assertEqual(data['status'], 'success')
        events = data['data']['events']
        
        # Find the security event
        sec_events = [e for e in events 
                     if e['event_type'] == AuditEvent.SECURITY_EVENT 
                     and e['action'] == event_name]
        
        self.assertTrue(len(sec_events) > 0)
        sec_event = sec_events[0]
        
        self.assertEqual(sec_event['actor_id'], 'test_user')
        self.assertEqual(sec_event['details']['severity'], severity)
        self.assertEqual(sec_event['details']['source_ip'], details['source_ip'])

    def test_automatic_request_auditing(self):
        """Test that HTTP requests are automatically audited."""
        # Make a series of different requests to generate audit events
        endpoints = [
            '/api/test/auth/login',
            '/api/test/data/document/doc123',
            '/api/test/security-event'
        ]
        
        for endpoint in endpoints:
            if endpoint == '/api/test/auth/login':
                self.client.post(
                    endpoint, 
                    json={'user_id': 'test_user', 'success': True},
                    content_type='application/json'
                )
            elif endpoint == '/api/test/data/document/doc123':
                self.client.get(endpoint)
            elif endpoint == '/api/test/security-event':
                self.client.post(
                    endpoint, 
                    json={'event_name': 'test_event', 'severity': 'low'},
                    content_type='application/json'
                )
        
        # Check for API request audit events
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        
        self.assertEqual(data['status'], 'success')
        events = data['data']['events']
        
        # Find API request events
        api_events = [e for e in events if e['event_type'] == AuditEvent.API_USAGE]
        
        # We should have at least one API event for each endpoint we hit
        self.assertTrue(len(api_events) >= len(endpoints))
        
        # Check that each endpoint has at least one corresponding event
        endpoint_counts = {endpoint: 0 for endpoint in endpoints}
        for event in api_events:
            for endpoint in endpoints:
                if endpoint in event['details'].get('path', ''):
                    endpoint_counts[endpoint] += 1
        
        for endpoint, count in endpoint_counts.items():
            self.assertTrue(count > 0, f"No audit event for endpoint {endpoint}")

    def test_event_retrieval_by_id(self):
        """Test retrieving a specific audit event by ID."""
        # Create an event first
        response = self.client.post(
            '/api/test/auth/login',
            json={'user_id': 'test_user', 'success': True},
            content_type='application/json'
        )
        
        # Get all events
        response = self.client.get('/api/test/admin/audit/events')
        data = json.loads(response.data)
        events = data['data']['events']
        
        # Get a specific event ID
        event_id = events[0]['event_id']
        
        # Retrieve that specific event
        response = self.client.get(f'/api/test/admin/audit/events/{event_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        retrieved_event = data['data']
        self.assertEqual(retrieved_event['event_id'], event_id)

    def test_integrity_verification(self):
        """Test the integrity verification feature."""
        # Create several events
        self.client.post(
            '/api/test/auth/login', 
            json={'user_id': 'user1', 'success': True},
            content_type='application/json'
        )
        self.client.get('/api/test/data/document/doc1')
        self.client.put(
            '/api/test/data/settings/settings1', 
            json={'changes': {'theme': 'light'}},
            content_type='application/json'
        )
        
        # Verify integrity
        response = self.client.post('/api/test/admin/audit/verify-integrity')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['data']['integrity_verified'])

    def test_filtering_and_pagination(self):
        """Test filtering and pagination of audit events."""
        # Create a variety of events
        # 1. Authentication events
        for i in range(3):
            self.client.post(
                '/api/test/auth/login',
                json={'user_id': f'user{i}', 'success': True},
                content_type='application/json'
            )
        
        # 2. Data access events
        for i in range(3):
            self.client.get(f'/api/test/data/document/doc{i}')
        
        # 3. Data modification events
        for i in range(3):
            self.client.put(
                f'/api/test/data/settings/settings{i}',
                json={'changes': {'setting': f'value{i}'}},
                content_type='application/json'
            )
        
        # 4. Security events
        for i in range(3):
            self.client.post(
                '/api/test/security-event',
                json={
                    'event_name': f'security_event_{i}',
                    'severity': 'medium',
                    'details': {'test': i}
                },
                content_type='application/json'
            )
        
        # Test filtering by event type
        response = self.client.get(
            '/api/test/admin/audit/events?event_type=user_authentication'
        )
        data = json.loads(response.data)
        events = data['data']['events']
        
        # All events should be authentication events
        for event in events:
            self.assertEqual(event['event_type'], AuditEvent.USER_AUTHENTICATION)
        
        # There should be at least 3 authentication events (we created 3)
        self.assertTrue(len(events) >= 3)
        
        # Test pagination
        response = self.client.get(
            '/api/test/admin/audit/events?page=1&page_size=5'
        )
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['data']['events']) <= 5)
        
        # Test combined filtering and pagination
        response = self.client.get(
            '/api/test/admin/audit/events?event_type=data_access&page=1&page_size=2'
        )
        data = json.loads(response.data)
        events = data['data']['events']
        
        # All events should be data access events
        for event in events:
            self.assertEqual(event['event_type'], AuditEvent.DATA_ACCESS)
        
        # There should be at most 2 events due to page_size
        self.assertTrue(len(events) <= 2)


if __name__ == '__main__':
    unittest.main()
