"""
Web content extraction tools for LangChain.

This module provides tools for extracting content from web pages, including
HTML parsing, text extraction, and metadata collection.
"""

import logging
import requests
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
import json
from urllib.parse import urlparse

from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from .utils import handle_request_error, extract_main_content, create_user_agent, is_valid_url

logger = logging.getLogger(__name__)

class ExtractContentInput(BaseModel):
    """Input schema for WebContentExtractionTool."""
    url: str = Field(..., description="URL of the web page to extract content from")
    elements: Optional[List[str]] = Field(
        default=None, 
        description="Specific elements to extract (e.g., ['article', 'main', 'h1'])"
    )
    include_metadata: bool = Field(
        default=True, 
        description="Whether to include metadata like title, links, and images"
    )
    timeout: int = Field(
        default=10, 
        description="Timeout in seconds for the HTTP request"
    )
    
    @validator('url')
    def validate_url(cls, v):
        if not is_valid_url(v):
            raise ValueError(f"Invalid URL format: {v}")
        return v

class WebContentExtractionTool(BaseTool):
    """Tool for extracting and processing content from web pages."""
    
    name: str = "web_content_extraction"
    description: str = """
    Extract content from a web page. Useful for getting the text content,
    links, images, and other information from a specific URL.
    Input should be a valid URL.
    """
    args_schema: type[BaseModel] = ExtractContentInput
    
    def _run(
        self, 
        url: str,
        elements: Optional[List[str]] = None,
        include_metadata: bool = True,
        timeout: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run the web content extraction tool."""
        try:
            # Set up headers with user agent to avoid being blocked
            headers = {
                'User-Agent': create_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            # Make the request to the URL
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Extract content using the utility function
            content, metadata = extract_main_content(response.text, url)
            
            # Extract specific elements if requested
            if elements:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    element_contents = {}
                    for element in elements:
                        # Handle both tag names and CSS selectors
                        found_elements = soup.select(element) if '.' in element or '#' in element else soup.find_all(element)
                        element_contents[element] = [elem.get_text(strip=True) for elem in found_elements]
                    
                    # Add extracted elements to the result
                    metadata["extracted_elements"] = element_contents
                except Exception as e:
                    logger.warning(f"Error extracting specific elements: {str(e)}")
                    metadata["extraction_error"] = str(e)
            
            # Prepare the result
            result = {
                "content": content,
                "url": url,
                "success": True,
            }
            
            # Include metadata if requested
            if include_metadata:
                result["metadata"] = metadata
            
            return result
            
        except requests.exceptions.RequestException as e:
            return handle_request_error(e, url)
        except Exception as e:
            logger.error(f"Unexpected error extracting content from {url}: {str(e)}")
            return {
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "url": url
            }
    
    async def _arun(
        self, 
        url: str,
        elements: Optional[List[str]] = None,
        include_metadata: bool = True,
        timeout: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run the web content extraction tool asynchronously."""
        # For simplicity, we're using the synchronous implementation
        # In a production environment, you would use aiohttp for async requests
        return self._run(url, elements, include_metadata, timeout, run_manager)


class StructuredContentExtractionTool(BaseTool):
    """Tool for extracting structured content from web pages based on a schema."""
    
    name: str = "structured_web_content_extraction"
    description: str = """
    Extract structured content from a web page according to a specified schema.
    Useful for extracting specific types of information like product details,
    article metadata, contact information, etc.
    
    Input should be a JSON with:
    - url: The web page URL to extract from
    - schema: Object describing the structure to extract (e.g., {"title": "h1", "price": ".product-price"})
    """
    
    def _run(
        self, 
        url: str,
        schema: Dict[str, str],
        timeout: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run the structured content extraction tool."""
        if not is_valid_url(url):
            return {"success": False, "error": f"Invalid URL: {url}"}
            
        if not schema or not isinstance(schema, dict):
            return {"success": False, "error": "Schema must be a non-empty dictionary"}
            
        try:
            # Set up headers with user agent to avoid being blocked
            headers = {
                'User-Agent': create_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Make the request to the URL
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Extract structured content using BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data according to the schema
            extracted_data = {}
            for key, selector in schema.items():
                try:
                    elements = soup.select(selector)
                    if len(elements) == 1:
                        # Single element, extract text
                        extracted_data[key] = elements[0].get_text(strip=True)
                    elif len(elements) > 1:
                        # Multiple elements, extract as list
                        extracted_data[key] = [elem.get_text(strip=True) for elem in elements]
                    else:
                        # No elements found
                        extracted_data[key] = None
                except Exception as e:
                    logger.warning(f"Error extracting {key} with selector {selector}: {str(e)}")
                    extracted_data[key] = None
            
            return {
                "success": True,
                "url": url,
                "extracted_data": extracted_data
            }
            
        except requests.exceptions.RequestException as e:
            return handle_request_error(e, url)
        except Exception as e:
            logger.error(f"Unexpected error in structured extraction from {url}: {str(e)}")
            return {
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "url": url
            }
    
    async def _arun(
        self, 
        url: str,
        schema: Dict[str, str],
        timeout: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run the structured content extraction tool asynchronously."""
        # For simplicity, we're using the synchronous implementation
        return self._run(url, schema, timeout, run_manager)
