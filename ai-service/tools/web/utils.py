"""
Utility functions for web tools used with LangChain.

This module provides helper functions for handling web requests, error handling,
content extraction, and other web-related utilities.
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

def handle_request_error(error: RequestException, url: str) -> Dict[str, Any]:
    """
    Handle request errors gracefully and return standardized error information.
    
    Args:
        error: The request exception that occurred
        url: The URL that caused the error
        
    Returns:
        A dictionary with error details
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    logger.error(f"Error accessing {url}: {error_type} - {error_message}")
    
    # Categorize errors for better handling by agents
    if isinstance(error, requests.exceptions.ConnectionError):
        error_category = "connection_error"
        suggestion = "Check network connection or URL validity"
    elif isinstance(error, requests.exceptions.Timeout):
        error_category = "timeout"
        suggestion = "Try again later or with a longer timeout"
    elif isinstance(error, requests.exceptions.TooManyRedirects):
        error_category = "too_many_redirects"
        suggestion = "Check URL for redirect loops"
    elif isinstance(error, requests.exceptions.HTTPError):
        error_category = "http_error"
        # Safely get status code if it exists
        status_code = None
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
        suggestion = f"HTTP error {status_code}" if status_code else "HTTP error occurred"
    else:
        error_category = "other"
        suggestion = "Unknown error, check URL and try again"
    
    return {
        "success": False,
        "error_type": error_type,
        "error_category": error_category,
        "error_message": error_message,
        "url": url,
        "suggestion": suggestion
    }

def extract_main_content(html_content: str, url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract the main content from an HTML page, attempting to remove navigation, 
    headers, footers, and other non-content elements.
    
    Args:
        html_content: Raw HTML content
        url: URL of the page (used to resolve relative links)
        
    Returns:
        Tuple containing (extracted_text, metadata)
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
            script_or_style.decompose()
            
        # Extract metadata
        metadata = {
            "title": soup.title.string if soup.title else None,
            "url": url,
            "links": [],
            "images": []
        }
        
        # Get base URL for resolving relative URLs
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Resolve relative URLs
            if href.startswith('/'):
                href = base_url + href
            elif not (href.startswith('http://') or href.startswith('https://')):
                # Skip javascript: links and anchors
                if href.startswith('#') or href.startswith('javascript:'):
                    continue
                href = url + ('/' if not url.endswith('/') else '') + href
                
            link_text = link.get_text(strip=True)
            if href and link_text:
                metadata["links"].append({
                    "url": href,
                    "text": link_text[:100]  # Truncate very long link text
                })
        
        # Extract images with alt text
        for img in soup.find_all('img', alt=True, src=True):
            src = img['src']
            # Resolve relative URLs
            if src.startswith('/'):
                src = base_url + src
            elif not (src.startswith('http://') or src.startswith('https://')):
                src = url + ('/' if not url.endswith('/') else '') + src
                
            metadata["images"].append({
                "url": src,
                "alt": img['alt']
            })
        
        # Extract main text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Attempt to find main content if text is too large
        if len(text) > 10000:
            main_content_candidates = soup.find_all(['article', 'main', 'div'], 
                                                    class_=['content', 'main', 'article', 'post'])
            if main_content_candidates:
                # Use the largest content block
                main_content = max(main_content_candidates, 
                                 key=lambda x: len(x.get_text()))
                text = main_content.get_text(separator='\n', strip=True)
        
        return text, metadata
    
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return f"Error extracting content: {str(e)}", {"url": url, "error": str(e)}

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: URL to check
        
    Returns:
        Boolean indicating if URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def create_user_agent() -> str:
    """
    Create a realistic user agent string for web requests.
    
    Returns:
        A user agent string
    """
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 TechSaaS.Tech/1.0"
