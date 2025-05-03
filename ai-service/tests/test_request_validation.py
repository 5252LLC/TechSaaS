"""
Tests for request validation middleware
"""

import unittest
import json
from flask import Flask, jsonify, g, request
from marshmallow import Schema, fields

# Import middleware
from api.v1.middleware.request_validation import (
    validate_json, 
    validate_schema, 
    validate_content_type,
    sanitize_input,
    validate_request
)

# Test schema for validation
class TestSchema(Schema):
    """Test schema for request validation"""
    name = fields.String(required=True)
    age = fields.Integer(required=True)
    email = fields.Email()

class RequestValidationTests(unittest.TestCase):
    """Test cases for request validation middleware"""
    
    def setUp(self):
        """Set up test Flask application"""
        self.app = Flask(__name__)
        
        # Test route with JSON validation
        @self.app.route('/test_json', methods=['POST'])
        @validate_json
        def test_json():
            data = request.get_json()
            return jsonify({'received': data})
        
        # Test route with schema validation
        @self.app.route('/test_schema', methods=['POST'])
        @validate_schema(TestSchema)
        def test_schema():
            # g.validated_data is set by the middleware
            return jsonify({'validated': g.validated_data})
        
        # Test route with content type validation
        @self.app.route('/test_content_type', methods=['POST'])
        @validate_content_type(['application/json', 'application/xml'])
        def test_content_type():
            return jsonify({'success': True})
        
        # Test route with sanitize input
        @self.app.route('/test_sanitize', methods=['POST'])
        @sanitize_input()
        def test_sanitize():
            return jsonify({'sanitized': g.sanitized_data})
        
        # Test route with combined validation
        @self.app.route('/test_combined', methods=['POST'])
        @validate_request(TestSchema)
        def test_combined():
            return jsonify({'validated': g.validated_data})
        
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
    def test_validate_json_success(self):
        """Test validate_json with valid JSON data"""
        response = self.client.post(
            '/test_json',
            data=json.dumps({'test': 'value'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['received']['test'], 'value')
        
    def test_validate_json_invalid_content_type(self):
        """Test validate_json with invalid content type"""
        response = self.client.post(
            '/test_json',
            data=json.dumps({'test': 'value'}),
            content_type='text/plain'
        )
        self.assertEqual(response.status_code, 415)  # Unsupported Media Type
        
    def test_validate_json_invalid_json(self):
        """Test validate_json with invalid JSON"""
        response = self.client.post(
            '/test_json',
            data='{"test": "value"',  # Invalid JSON (missing closing brace)
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)  # Bad Request
        
    def test_validate_schema_success(self):
        """Test schema validation with valid data"""
        response = self.client.post(
            '/test_schema',
            data=json.dumps({
                'name': 'Test User',
                'age': 30,
                'email': 'test@example.com'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['validated']['name'], 'Test User')
        
    def test_validate_schema_missing_required(self):
        """Test schema validation with missing required field"""
        response = self.client.post(
            '/test_schema',
            data=json.dumps({
                'name': 'Test User'
                # 'age' is missing
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('details', data)
        self.assertIn('age', data['details'])
        
    def test_validate_schema_invalid_field(self):
        """Test schema validation with invalid field"""
        response = self.client.post(
            '/test_schema',
            data=json.dumps({
                'name': 'Test User',
                'age': 30,
                'email': 'not-an-email'  # Invalid email
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('details', data)
        self.assertIn('email', data['details'])
        
    def test_validate_content_type_success(self):
        """Test content type validation with valid content type"""
        response = self.client.post(
            '/test_content_type',
            data=json.dumps({'test': 'value'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(
            '/test_content_type',
            data='<test>value</test>',
            content_type='application/xml'
        )
        self.assertEqual(response.status_code, 200)
        
    def test_validate_content_type_invalid(self):
        """Test content type validation with invalid content type"""
        response = self.client.post(
            '/test_content_type',
            data='test value',
            content_type='text/plain'
        )
        self.assertEqual(response.status_code, 415)  # Unsupported Media Type
        
    def test_sanitize_input_script_tags(self):
        """Test input sanitization removes script tags"""
        response = self.client.post(
            '/test_sanitize',
            data=json.dumps({
                'text': 'Hello <script>alert("XSS");</script> World'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['sanitized']['text'], 'Hello  World')
        
    def test_combined_validation(self):
        """Test combined validation decorator"""
        response = self.client.post(
            '/test_combined',
            data=json.dumps({
                'name': 'Test User',
                'age': 30,
                'email': 'test@example.com'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['validated']['name'], 'Test User')
        
        # Test with invalid data
        response = self.client.post(
            '/test_combined',
            data=json.dumps({
                'name': 'Test User',
                # 'age' is missing
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
if __name__ == '__main__':
    unittest.main()
