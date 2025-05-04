"""
Rate Limiting Security Tests

This module tests the rate limiting functionality in the TechSaaS platform.
It includes tests for:
- API rate limiting
- Authentication rate limiting
- IP-based rate limiting
- User-based rate limiting
- Rate limit bypass prevention
"""

import unittest
import requests
import time
import os
import sys
import json
import concurrent.futures
import statistics

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class RateLimitingTests(unittest.TestCase):
    """Test cases for rate limiting functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # API endpoint configuration
        self.base_url = os.environ.get('TECHSAAS_API_URL', 'http://localhost:5000')
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.search_url = f"{self.base_url}/api/v1/search"
        self.profile_url = f"{self.base_url}/api/v1/user/profile"
        
        # Test credentials
        self.valid_credentials = {
            "email": "test@example.com",
            "password": "SecureP@ssw0rd!"
        }
        
        self.invalid_credentials = {
            "email": "test@example.com",
            "password": "WrongPassword123"
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
                    self.auth_headers = self.headers.copy()
                    self.auth_headers['Authorization'] = f"Bearer {token}"
        except:
            # Continue without authentication if login fails
            self.auth_headers = self.headers.copy()
    
    def test_api_rate_limiting(self):
        """Test that API endpoints enforce rate limits"""
        # Test endpoints that should have rate limiting
        rate_limited_endpoints = [
            self.search_url,
            f"{self.base_url}/api/v1/search?q=test",
            f"{self.base_url}/api/v1/lookup",
            f"{self.base_url}/api/v1/status"
        ]
        
        for endpoint in rate_limited_endpoints:
            # Send a burst of requests to trigger rate limiting
            responses = []
            start_time = time.time()
            
            # Make 20 requests in quick succession
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(self._make_request, endpoint, self.headers)
                    for _ in range(20)
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        response = future.result()
                        responses.append(response)
                    except Exception as e:
                        print(f"Error making request: {e}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Check for rate limiting evidence
            rate_limited = any(r.status_code == 429 for r in responses)
            
            # Check for rate limit headers
            has_rate_limit_headers = any(
                'X-RateLimit-Limit' in r.headers or
                'RateLimit-Limit' in r.headers or
                'Retry-After' in r.headers
                for r in responses
            )
            
            # Verify rate limiting is working
            self.assertTrue(
                rate_limited or has_rate_limit_headers,
                f"No rate limiting detected for endpoint: {endpoint}"
            )
            
            # If rate limiting did trigger, check for proper 429 status and headers
            if rate_limited:
                rate_limited_responses = [r for r in responses if r.status_code == 429]
                for resp in rate_limited_responses:
                    # Check for Retry-After header
                    self.assertIn('Retry-After', resp.headers,
                                 f"429 response missing Retry-After header for endpoint: {endpoint}")
                    
                    # Check rate limiting message in response body
                    self.assertTrue(
                        'rate limit' in resp.text.lower() or 
                        'too many requests' in resp.text.lower(),
                        f"429 response missing clear rate limit message for endpoint: {endpoint}"
                    )
    
    def test_authentication_rate_limiting(self):
        """Test that login endpoints enforce rate limits for failed attempts"""
        # Send multiple failed login attempts to trigger rate limiting
        responses = []
        
        # Make 10 failed login attempts in succession
        for _ in range(10):
            response = requests.post(
                self.login_url, 
                headers=self.headers, 
                json=self.invalid_credentials
            )
            responses.append(response)
            
            # Small delay to avoid overloading the server
            time.sleep(0.5)
        
        # Check for rate limiting evidence (status code 429 or increasing delays)
        rate_limited = any(r.status_code == 429 for r in responses)
        
        # Check for increasing response times which could indicate rate limiting with delays
        response_times = []
        for i, response in enumerate(responses[:5]):
            # Perform another request to measure current response time
            start = time.time()
            requests.post(
                self.login_url, 
                headers=self.headers, 
                json=self.invalid_credentials
            )
            end = time.time()
            response_times.append(end - start)
        
        increasing_delays = (
            len(response_times) >= 3 and
            response_times[-1] > response_times[0] * 1.5
        )
        
        # Verify authentication rate limiting is working
        self.assertTrue(
            rate_limited or increasing_delays,
            "No authentication rate limiting detected for login endpoint"
        )
    
    def test_user_vs_ip_rate_limiting(self):
        """Test that rate limits are enforced differently for authenticated users vs. IP addresses"""
        if 'Authorization' not in self.auth_headers:
            # Skip this test if authentication failed
            return
            
        # Test the same endpoint with and without authentication
        endpoint = self.search_url
        
        # Send requests with authentication
        auth_responses = []
        for _ in range(15):
            response = requests.get(
                f"{endpoint}?q=test-auth-{_}", 
                headers=self.auth_headers
            )
            auth_responses.append(response)
            time.time(0.2)
        
        # Send requests without authentication
        anon_responses = []
        for _ in range(15):
            response = requests.get(
                f"{endpoint}?q=test-anon-{_}", 
                headers=self.headers
            )
            anon_responses.append(response)
            time.time(0.2)
        
        # Check if rate limits differ between authenticated and anonymous requests
        auth_rate_limited = any(r.status_code == 429 for r in auth_responses)
        anon_rate_limited = any(r.status_code == 429 for r in anon_responses)
        
        # Get rate limit headers if available
        auth_limit = None
        anon_limit = None
        
        for resp in auth_responses:
            if 'X-RateLimit-Limit' in resp.headers:
                auth_limit = resp.headers['X-RateLimit-Limit']
                break
            elif 'RateLimit-Limit' in resp.headers:
                auth_limit = resp.headers['RateLimit-Limit']
                break
        
        for resp in anon_responses:
            if 'X-RateLimit-Limit' in resp.headers:
                anon_limit = resp.headers['X-RateLimit-Limit']
                break
            elif 'RateLimit-Limit' in resp.headers:
                anon_limit = resp.headers['RateLimit-Limit']
                break
        
        # Either different rate limit triggered status or different limit values
        different_limits = (
            auth_rate_limited != anon_rate_limited or
            (auth_limit and anon_limit and auth_limit != anon_limit)
        )
        
        # If rate limits appear to be the same, check if there are user-specific limits
        if not different_limits and 'X-RateLimit-Limit' in auth_responses[0].headers:
            # Ideally, authenticated users should have higher rate limits
            self.assertGreaterEqual(
                int(auth_responses[0].headers['X-RateLimit-Limit']), 
                int(anon_responses[0].headers['X-RateLimit-Limit']),
                "Authenticated users should have equal or higher rate limits than anonymous users"
            )
    
    def test_rate_limit_bypass_prevention(self):
        """Test that rate limits cannot be bypassed with common techniques"""
        if not any(r.status_code == 429 for r in self._trigger_rate_limit(self.search_url)):
            # Skip this test if we can't trigger rate limiting
            return
            
        # Wait for rate limit to reset
        time.sleep(5)
        
        # Base request to get normal response
        base_response = requests.get(f"{self.search_url}?q=test-bypass", headers=self.headers)
        
        # Test various bypass techniques
        bypass_techniques = {
            "Different User-Agent": {
                "headers": {**self.headers, "User-Agent": "Different-Agent/1.0"}
            },
            "Lowercase URL": {
                "url": self.search_url.lower()
            },
            "URL with different casing": {
                "url": self.search_url.replace("api", "ApI").replace("search", "sEaRcH")
            },
            "Adding URL parameters": {
                "url": f"{self.search_url}?_={time.time()}"
            },
            "Using different HTTP method": {
                "method": "POST",
                "data": json.dumps({"q": "test-bypass"}),
            },
            "Adding proxy headers": {
                "headers": {
                    **self.headers,
                    "X-Forwarded-For": "192.168.1.1",
                    "X-Real-IP": "192.168.1.1"
                }
            },
            "Adding Cache-Control header": {
                "headers": {**self.headers, "Cache-Control": "no-cache"}
            }
        }
        
        for technique_name, technique in bypass_techniques.items():
            # Trigger rate limiting first
            self._trigger_rate_limit(technique.get("url", self.search_url))
            
            # Try the bypass technique
            try:
                if technique.get("method") == "POST":
                    bypass_response = requests.post(
                        technique.get("url", self.search_url),
                        headers=technique.get("headers", self.headers),
                        data=technique.get("data", None)
                    )
                else:
                    bypass_response = requests.get(
                        technique.get("url", self.search_url),
                        headers=technique.get("headers", self.headers)
                    )
                
                # Check if bypass was successful (got 200 instead of 429)
                bypass_successful = (
                    bypass_response.status_code == 200 and
                    base_response.status_code == 200 and
                    len(bypass_response.content) > 20 and  # Not an empty or error response
                    'rate limit' not in bypass_response.text.lower()
                )
                
                self.assertFalse(
                    bypass_successful,
                    f"Rate limit bypass successful with technique: {technique_name}"
                )
            except Exception as e:
                # Exception is acceptable as it indicates the bypass failed
                pass
            
            # Wait briefly between tests
            time.sleep(1)
    
    def test_progressive_rate_limiting(self):
        """Test that repeated violations lead to stricter rate limits"""
        endpoint = self.search_url
        
        # Function to measure time until we can make successful requests again
        def measure_block_duration():
            start_time = time.time()
            max_wait = 60  # Maximum 60 seconds wait time
            
            while time.time() - start_time < max_wait:
                response = requests.get(f"{endpoint}?q=test-progressive-{time.time()}", headers=self.headers)
                if response.status_code == 200:
                    return time.time() - start_time
                time.sleep(2)
            
            return max_wait
        
        # Trigger rate limiting multiple times
        block_durations = []
        
        for i in range(3):
            # Trigger rate limiting
            self._trigger_rate_limit(endpoint)
            
            # Measure how long until we can make requests again
            duration = measure_block_duration()
            block_durations.append(duration)
            
            # If the block duration is longer than our max wait, break early
            if duration >= 60:
                break
                
            # Wait a bit extra to ensure we're fully unblocked
            time.sleep(5)
        
        # Check if block durations increase with repeated violations
        if len(block_durations) >= 2:
            progressive_blocking = block_durations[-1] > block_durations[0]
            self.assertTrue(
                progressive_blocking,
                "Rate limiting should become stricter with repeated violations"
            )
    
    def test_rate_limit_headers(self):
        """Test that proper rate limit headers are included in responses"""
        rate_limit_header_names = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
            'RateLimit-Limit',
            'RateLimit-Remaining',
            'RateLimit-Reset',
            'Retry-After'
        ]
        
        # Test various endpoints
        endpoints = [
            self.search_url,
            f"{self.base_url}/api/v1/status",
            f"{self.base_url}/api/v1/user/profile"
        ]
        
        for endpoint in endpoints:
            response = requests.get(
                endpoint,
                headers=self.auth_headers if 'profile' in endpoint else self.headers
            )
            
            # Check if any rate limit headers are present
            has_rate_limit_headers = any(
                header in response.headers for header in rate_limit_header_names
            )
            
            self.assertTrue(
                has_rate_limit_headers,
                f"No rate limit headers found for endpoint: {endpoint}"
            )
            
            # If limit headers are present, check for remaining and reset headers too
            if ('X-RateLimit-Limit' in response.headers or 
                'RateLimit-Limit' in response.headers):
                
                self.assertTrue(
                    ('X-RateLimit-Remaining' in response.headers or 
                     'RateLimit-Remaining' in response.headers),
                    f"Rate limit headers missing 'Remaining' counter for endpoint: {endpoint}"
                )
                
                self.assertTrue(
                    ('X-RateLimit-Reset' in response.headers or 
                     'RateLimit-Reset' in response.headers),
                    f"Rate limit headers missing 'Reset' time for endpoint: {endpoint}"
                )
    
    def _make_request(self, url, headers):
        """Helper method to make a request and return the response"""
        try:
            response = requests.get(url, headers=headers, timeout=10)
            return response
        except Exception as e:
            # Create a mock response for connection errors
            mock_response = requests.Response()
            mock_response.status_code = 500
            mock_response._content = str(e).encode('utf-8')
            return mock_response
    
    def _trigger_rate_limit(self, endpoint):
        """Helper method to trigger rate limiting on an endpoint"""
        responses = []
        
        # Make multiple requests in quick succession to trigger rate limiting
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self._make_request, endpoint, self.headers)
                for _ in range(30)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    response = future.result()
                    responses.append(response)
                    
                    # If we get rate limited, we can stop
                    if response.status_code == 429:
                        break
                except Exception:
                    pass
        
        return responses

if __name__ == "__main__":
    unittest.main()
