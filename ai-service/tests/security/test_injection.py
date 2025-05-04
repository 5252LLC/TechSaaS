"""
Injection Security Tests

This module tests protection against various injection attacks, including:
- SQL injection
- Command injection
- LDAP injection
- NoSQL injection
- Template injection
"""

import unittest
import requests
import json
import os
import sys
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class InjectionSecurityTests(unittest.TestCase):
    """Test cases for injection attack protection"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.search_url = f"{self.base_url}/api/v1/search"
        self.user_profile_url = f"{self.base_url}/api/v1/user"
        
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
        
        # Login to get authentication token
        try:
            login_response = requests.post(
                self.login_url, 
                headers=self.headers, 
                json=self.valid_credentials,
                timeout=5
            )
            
            if login_response.status_code == 200:
                token = login_response.json().get('access_token')
                if token:
                    self.headers['Authorization'] = f"Bearer {token}"
        except:
            # Continue without authentication if login fails
            pass
    
    def test_sql_injection_login(self):
        """Test protection against SQL injection in login form"""
        sql_injection_payloads = [
            {"email": "' OR 1=1 --", "password": "anything"},
            {"email": "admin' --", "password": "anything"},
            {"email": "' UNION SELECT 1,2,3,4,5 --", "password": "anything"},
            {"email": "'; DROP TABLE users; --", "password": "anything"},
            {"email": "' OR '1'='1", "password": "' OR '1'='1"},
            {"email": "user@example.com' OR 1=1 --", "password": "anything"},
        ]
        
        for payload in sql_injection_payloads:
            response = requests.post(self.login_url, headers=self.headers, json=payload)
            
            # Authentication should fail for malicious inputs
            self.assertNotEqual(response.status_code, 200, 
                               f"SQL injection potentially successful with: {payload}")
            self.assertNotIn('access_token', response.text, 
                           f"SQL injection may have bypassed authentication: {payload}")
    
    def test_sql_injection_search(self):
        """Test protection against SQL injection in search functionality"""
        sql_injection_payloads = [
            "' OR 1=1 --",
            "'; SELECT * FROM users; --",
            "' UNION SELECT username, password FROM users --",
            "'; DROP TABLE users; --",
            "a' OR 'a'='a",
            "\' OR \'\'=\'",
            "1' OR '1'='1'",
            "1 OR 1=1",
        ]
        
        for payload in sql_injection_payloads:
            # Test in URL parameters
            response = requests.get(f"{self.search_url}?q={payload}", headers=self.headers)
            self.assertFalse(
                self._contains_database_error(response), 
                f"Search parameter vulnerable to SQL injection: {payload}"
            )
            
            # Test in JSON body
            json_payload = {"query": payload}
            response = requests.post(self.search_url, headers=self.headers, json=json_payload)
            self.assertFalse(
                self._contains_database_error(response), 
                f"Search JSON payload vulnerable to SQL injection: {payload}"
            )
    
    def test_command_injection(self):
        """Test protection against command injection attacks"""
        command_injection_payloads = [
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "; ls -la",
            "& whoami",
            "$(cat /etc/passwd)",
            "`cat /etc/passwd`",
            "|| cat /etc/passwd",
            "& ping -c 4 attacker.com &",
            "'; exec(\"import os; os.system('id')\"); '",
        ]
        
        for payload in command_injection_payloads:
            # Test in URL parameters where file or system operations might be performed
            download_url = f"{self.base_url}/api/v1/download?file={payload}"
            response = requests.get(download_url, headers=self.headers)
            
            # Check for evidence of command execution in response
            self.assertFalse(
                self._contains_command_execution_evidence(response),
                f"Endpoint potentially vulnerable to command injection: {payload}"
            )
            
            # Test in JSON body
            profile_data = {"profileImage": f"profile{payload}.jpg"}
            response = requests.put(self.user_profile_url, headers=self.headers, json=profile_data)
            
            self.assertFalse(
                self._contains_command_execution_evidence(response),
                f"Profile update potentially vulnerable to command injection: {payload}"
            )
    
    def test_nosql_injection(self):
        """Test protection against NoSQL injection attacks"""
        nosql_injection_payloads = [
            {"email": {"$ne": None}, "password": {"$ne": None}},
            {"email": {"$in": ["admin@example.com", "test@example.com"]}, "password": {"$gt": ""}},
            {"email": "test@example.com", "password": {"$regex": "^p"}},
            {"email": {"$exists": True}, "password": {"$exists": True}},
            {"$where": "function() { return true; }"},
            {"email": {"$gt": ""}, "password": {"$gt": ""}},
        ]
        
        for payload in nosql_injection_payloads:
            response = requests.post(self.login_url, headers=self.headers, json=payload)
            
            # Authentication should fail for malicious inputs
            self.assertNotEqual(response.status_code, 200, 
                              f"NoSQL injection potentially successful with: {payload}")
            
            # Also check that the server properly handles the invalid input without exposing details
            self.assertFalse(
                "$" in response.text and "mongo" in response.text.lower(), 
                f"NoSQL error details exposed: {payload}"
            )
    
    def test_ldap_injection(self):
        """Test protection against LDAP injection attacks"""
        ldap_injection_payloads = [
            {"username": "*)(uid=*))(|(uid=*", "password": "anything"},
            {"username": "admin)(&))", "password": "anything"},
            {"username": "*)(|(password=*))", "password": "anything"},
            {"username": "*)*", "password": "anything"},
            {"username": "admin)(|(objectclass=*)", "password": "anything"},
        ]
        
        # Assuming LDAP auth is at /api/v1/auth/ldap
        ldap_auth_url = f"{self.base_url}/api/v1/auth/ldap"
        
        for payload in ldap_injection_payloads:
            try:
                response = requests.post(ldap_auth_url, headers=self.headers, json=payload)
                
                # Authentication should fail for malicious inputs
                self.assertNotEqual(response.status_code, 200, 
                                  f"LDAP injection potentially successful with: {payload}")
                
                # Check for LDAP error leakage
                self.assertFalse(
                    "ldap" in response.text.lower() and "error" in response.text.lower(),
                    f"LDAP error details exposed: {payload}"
                )
            except:
                # If endpoint doesn't exist, that's acceptable
                pass
    
    def test_template_injection(self):
        """Test protection against template injection attacks"""
        template_injection_payloads = [
            "{{7*7}}",
            "${7*7}",
            "<%= 7*7 %>",
            "{7*7}",
            "#{7*7}",
            "{{config}}",
            "{{self.__init__.__globals__}}",
            "${T(java.lang.Runtime).getRuntime().exec('touch /tmp/pwned')}",
            "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
        ]
        
        # Test in endpoints that might use template engines
        template_endpoints = [
            f"{self.base_url}/api/v1/email/preview",
            f"{self.base_url}/api/v1/dashboard/widget",
            f"{self.base_url}/api/v1/export/template",
        ]
        
        for endpoint in template_endpoints:
            for payload in template_injection_payloads:
                # Test in URL parameters
                response = requests.get(f"{endpoint}?name={payload}", headers=self.headers)
                
                # Check for template evaluation evidence (e.g., "49" from 7*7)
                self.assertFalse(
                    "49" in response.text and payload in response.text,
                    f"Endpoint potentially vulnerable to template injection via URL: {endpoint} with {payload}"
                )
                
                # Test in JSON body
                json_payload = {"template": payload, "name": payload}
                response = requests.post(endpoint, headers=self.headers, json=json_payload)
                
                self.assertFalse(
                    "49" in response.text and payload in response.text,
                    f"Endpoint potentially vulnerable to template injection via JSON: {endpoint} with {payload}"
                )
    
    def _contains_database_error(self, response):
        """Check if the response contains evidence of a database error"""
        error_indicators = [
            "sql", "database", "syntax error", "mysql", "postgresql", "sqlite",
            "ora-", "db2", "odbc", "sybase", "driver", "data source", "select",
            "insert", "update", "delete", "union", "where", "from", "table", "column"
        ]
        
        response_text = response.text.lower()
        for indicator in error_indicators:
            if indicator in response_text and "error" in response_text:
                return True
        
        return False
    
    def _contains_command_execution_evidence(self, response):
        """Check if the response contains evidence of successful command execution"""
        command_output_indicators = [
            "uid=", "gid=", "root:", "bin:", "etc/passwd", "etc/shadow",
            "bash", "groups=", "linux", "windows", "system32", "cmd.exe",
            "powershell", "usr/bin", "bin/sh", "tmp/", "proc/"
        ]
        
        response_text = response.text.lower()
        for indicator in command_output_indicators:
            if indicator in response_text:
                return True
        
        return False

if __name__ == "__main__":
    unittest.main()
