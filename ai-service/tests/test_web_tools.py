"""
Tests for web tools used with LangChain.

This module provides unit tests for the web search and content extraction tools.
"""

import unittest
from unittest.mock import patch, MagicMock
import requests
import json
import os
import sys
from typing import Optional, Dict, Any, List

# Add the parent directory to the path to import the tools
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.web.extraction import WebContentExtractionTool, StructuredContentExtractionTool
from tools.web.search import WebSearchTool, NoAPIWebSearchTool
from tools.web.utils import handle_request_error, extract_main_content, is_valid_url, create_user_agent

class TestWebContentExtractionTool(unittest.TestCase):
    """Test the WebContentExtractionTool."""
    
    @patch('requests.get')
    def test_extract_content_success(self, mock_get):
        """Test successful content extraction."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Heading</h1>
                <article>
                    <p>This is a test paragraph.</p>
                    <a href="https://example.com">Test Link</a>
                    <img src="test.jpg" alt="Test Image">
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Initialize the tool and run it
        tool = WebContentExtractionTool()
        result = tool._run(url="https://example.com")
        
        # Assert the result has the expected structure
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://example.com")
        self.assertIn("content", result)
        self.assertIn("metadata", result)
        
        # Check that the content and metadata extraction worked
        self.assertIn("Test Heading", result["content"])
        self.assertIn("test paragraph", result["content"])
        self.assertEqual(result["metadata"]["title"], "Test Page")
        self.assertEqual(len(result["metadata"]["links"]), 1)
        self.assertEqual(len(result["metadata"]["images"]), 1)
    
    @patch('requests.get')
    def test_extract_content_with_elements(self, mock_get):
        """Test content extraction with specific elements."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Heading</h1>
                <article>
                    <p>This is a test paragraph.</p>
                    <p>This is another paragraph.</p>
                </article>
                <div class="sidebar">Sidebar content</div>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Initialize the tool and run it with specific elements
        tool = WebContentExtractionTool()
        result = tool._run(url="https://example.com", elements=["h1", "p", ".sidebar"])
        
        # Check that the elements were extracted correctly
        self.assertIn("extracted_elements", result["metadata"])
        self.assertEqual(len(result["metadata"]["extracted_elements"]["h1"]), 1)
        self.assertEqual(len(result["metadata"]["extracted_elements"]["p"]), 2)
        self.assertEqual(len(result["metadata"]["extracted_elements"][".sidebar"]), 1)
        self.assertEqual(result["metadata"]["extracted_elements"]["h1"][0], "Test Heading")
        self.assertIn("test paragraph", result["metadata"]["extracted_elements"]["p"][0])
        self.assertEqual(result["metadata"]["extracted_elements"][".sidebar"][0], "Sidebar content")
    
    @patch('requests.get')
    def test_extract_content_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        # Mock the exception
        mock_get.side_effect = requests.exceptions.HTTPError("404 Client Error")
        
        # Initialize the tool and run it
        tool = WebContentExtractionTool()
        result = tool._run(url="https://example.com")
        
        # Assert the error handling worked
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "HTTPError")
        self.assertEqual(result["url"], "https://example.com")

class TestStructuredContentExtractionTool(unittest.TestCase):
    """Test the StructuredContentExtractionTool."""
    
    @patch('requests.get')
    def test_structured_extraction(self, mock_get):
        """Test structured content extraction."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><title>Product Page</title></head>
            <body>
                <h1 class="product-title">Test Product</h1>
                <div class="product-price">$99.99</div>
                <div class="product-description">This is a test product description.</div>
                <ul class="features">
                    <li>Feature 1</li>
                    <li>Feature 2</li>
                </ul>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Initialize the tool and run it with a schema
        tool = StructuredContentExtractionTool()
        schema = {
            "title": ".product-title",
            "price": ".product-price",
            "description": ".product-description",
            "features": ".features li"
        }
        result = tool._run(url="https://example.com", schema=schema)
        
        # Assert the extraction worked as expected
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://example.com")
        self.assertIn("extracted_data", result)
        
        # Check the extracted data matches the schema
        self.assertEqual(result["extracted_data"]["title"], "Test Product")
        self.assertEqual(result["extracted_data"]["price"], "$99.99")
        self.assertEqual(result["extracted_data"]["description"], "This is a test product description.")
        self.assertEqual(len(result["extracted_data"]["features"]), 2)
        self.assertEqual(result["extracted_data"]["features"][0], "Feature 1")

class TestWebSearchTool(unittest.TestCase):
    """Test the WebSearchTool."""
    
    @patch('requests.get')
    def test_web_search_with_api(self, mock_get):
        """Test web search with API."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Result 1",
                    "link": "https://example.com/1",
                    "snippet": "This is test result 1."
                },
                {
                    "title": "Test Result 2",
                    "link": "https://example.com/2",
                    "snippet": "This is test result 2."
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Initialize the tool with mock API credentials
        tool = WebSearchTool(api_key="test_key", engine_id="test_engine")
        results = tool._run(query="test query", num_results=2)
        
        # Assert the results are as expected
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Test Result 1")
        self.assertEqual(results[0]["link"], "https://example.com/1")
        self.assertEqual(results[0]["snippet"], "This is test result 1.")
        self.assertEqual(results[0]["source"], "google_api")
    
    @patch('tools.web.search.NoAPIWebSearchTool._run')
    def test_web_search_fallback(self, mock_no_api_run):
        """Test fallback to NoAPIWebSearchTool when no API key is available."""
        # Mock the fallback method
        mock_no_api_run.return_value = [
            {
                "title": "Fallback Result",
                "link": "https://example.com/fallback",
                "snippet": "This is a fallback result.",
                "source": "duckduckgo"
            }
        ]
        
        # Initialize the tool without API credentials
        tool = WebSearchTool(api_key="", engine_id="")
        results = tool._run(query="test query")
        
        # Assert that the fallback method was called
        mock_no_api_run.assert_called_once()
        
        # Check the results from the fallback
        self.assertEqual(results[0]["title"], "Fallback Result")
        self.assertEqual(results[0]["source"], "duckduckgo")

class TestWebUtils(unittest.TestCase):
    """Test web utility functions."""
    
    def test_is_valid_url(self):
        """Test URL validation."""
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/path?query=test"))
        self.assertFalse(is_valid_url("not a url"))
        self.assertFalse(is_valid_url("example.com"))  # Missing scheme
    
    def test_create_user_agent(self):
        """Test user agent creation."""
        user_agent = create_user_agent()
        self.assertIsInstance(user_agent, str)
        self.assertIn("TechSaaS.Tech", user_agent)
    
    def test_handle_request_error(self):
        """Test request error handling."""
        error = requests.exceptions.ConnectionError("Connection refused")
        result = handle_request_error(error, "https://example.com")
        
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "ConnectionError")
        self.assertEqual(result["error_category"], "connection_error")
        self.assertEqual(result["url"], "https://example.com")
    
    def test_extract_main_content(self):
        """Test main content extraction."""
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <nav>Navigation</nav>
                <article>Main content</article>
                <footer>Footer</footer>
            </body>
        </html>
        """
        content, metadata = extract_main_content(html, "https://example.com")
        
        self.assertIn("Main content", content)
        self.assertNotIn("Navigation", content)
        self.assertNotIn("Footer", content)
        self.assertEqual(metadata["title"], "Test")
        self.assertEqual(metadata["url"], "https://example.com")

if __name__ == '__main__':
    unittest.main()
