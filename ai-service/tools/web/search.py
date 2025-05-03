"""
Web search tools for LangChain.

This module provides tools for performing web searches using different backends,
including wrapper utilities for API-based search and fallback search mechanisms.
"""

import logging
import requests
import json
import os
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
import urllib.parse
from bs4 import BeautifulSoup

from langchain_core.tools import BaseTool
from langchain_core.callbacks.manager import CallbackManagerForToolRun

from .utils import handle_request_error, create_user_agent, is_valid_url

logger = logging.getLogger(__name__)

# Default search API keys - should be moved to a proper config in production
DEFAULT_SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
DEFAULT_SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID", "")

class SearchResult(BaseModel):
    """Schema for a search result."""
    title: str
    link: str
    snippet: str
    source: Optional[str] = None
    position: Optional[int] = None

class WebSearchInput(BaseModel):
    """Input schema for WebSearchTool."""
    query: str = Field(..., description="Search query string")
    num_results: int = Field(
        default=5, 
        description="Number of search results to return (1-10)"
    )
    
    @validator('num_results')
    def validate_num_results(cls, v):
        if v < 1 or v > 10:
            raise ValueError("num_results must be between 1 and 10")
        return v

class WebSearchTool(BaseTool):
    """Tool for performing web searches using a search API."""
    
    name: str = "web_search"
    description: str = """
    Search the web for information on a specific topic.
    Returns search results with titles, snippets, and links.
    Input should be a search query string.
    """
    args_schema: type[BaseModel] = WebSearchInput
    
    # Define fields to store credentials as class vars not model fields
    _api_key: str = ""
    _engine_id: str = ""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        engine_id: Optional[str] = None,
        **kwargs
    ):
        """Initialize with optional API key and engine ID."""
        super().__init__(**kwargs)
        self._api_key = api_key or DEFAULT_SEARCH_API_KEY
        self._engine_id = engine_id or DEFAULT_SEARCH_ENGINE_ID
        
        if not self._api_key:
            logger.warning("No search API key provided. Search functionality will be limited.")
    
    def _run(
        self,
        query: str,
        num_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, str]]:
        """Run the web search tool."""
        try:
            # URL encode the query
            encoded_query = urllib.parse.quote_plus(query)
            
            # Check if we have API credentials
            if not self._api_key or not self._engine_id:
                # Fallback to NoAPIWebSearchTool if no API key is available
                logger.info("No API key, falling back to No-API search")
                fallback_tool = NoAPIWebSearchTool()
                return fallback_tool._run(query=query, num_results=num_results, run_manager=run_manager)
            
            # Use Google Custom Search API
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self._api_key,
                "cx": self._engine_id,
                "q": encoded_query,
                "num": min(num_results, 10),  # API limit is 10
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "items" not in data:
                return [{
                    "title": "No results found",
                    "link": "",
                    "snippet": f"No search results found for query: {query}",
                    "source": "google_api"
                }]
            
            # Parse the results
            results = []
            for idx, item in enumerate(data["items"][:num_results]):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google_api",
                    "position": idx + 1
                })
            
            return results
            
        except requests.exceptions.RequestException as e:
            error_info = handle_request_error(e, "search_api")
            return [{
                "title": f"Error: {error_info['error_type']}",
                "link": "",
                "snippet": error_info["error_message"],
                "source": "error"
            }]
            
        except Exception as e:
            logger.error(f"Unexpected error in web search: {str(e)}")
            return [{
                "title": f"Error: {type(e).__name__}",
                "link": "",
                "snippet": str(e),
                "source": "error"
            }]
    
    async def _arun(
        self,
        query: str,
        num_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, str]]:
        """Run the web search tool asynchronously."""
        # For simplicity, we're using the synchronous implementation
        return self._run(query, num_results, run_manager)

class NoAPIWebSearchTool(BaseTool):
    """
    Tool for performing web searches without requiring an API key.
    This is a fallback method that scrapes search results directly from search engines.
    Note: This approach is less reliable and may violate some terms of service.
    """
    
    name: str = "no_api_web_search"
    description: str = """
    Search the web without requiring an API key.
    Note that this method is less reliable than API-based searches.
    Input should be a search query string.
    """
    args_schema: type[BaseModel] = WebSearchInput
    
    def _run(
        self,
        query: str,
        num_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, str]]:
        """Run the no-API web search tool."""
        try:
            # URL encode the query
            encoded_query = urllib.parse.quote_plus(query)
            
            # Use DuckDuckGo as it's more scraper-friendly
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            headers = {
                'User-Agent': create_user_agent(),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://duckduckgo.com/',
                'DNT': '1',
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result elements
            results = []
            result_elements = soup.select('.result')[:num_results]
            
            for idx, result in enumerate(result_elements):
                title_element = result.select_one('.result__title')
                link_element = result.select_one('.result__url')
                snippet_element = result.select_one('.result__snippet')
                
                title = title_element.get_text(strip=True) if title_element else "No title"
                
                # Extract the actual link
                if link_element:
                    link = link_element.get('href', '')
                    # Clean up the link if it's a redirect URL
                    if '/rd/' in link:
                        try:
                            link = link.split('/rd/')[1].split('?')[0]
                            link = urllib.parse.unquote(link)
                        except:
                            pass
                else:
                    link = ""
                
                snippet = snippet_element.get_text(strip=True) if snippet_element else "No description available"
                
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "source": "duckduckgo",
                    "position": idx + 1
                })
            
            # If we didn't find any results, return a message
            if not results:
                return [{
                    "title": "No results found",
                    "link": "",
                    "snippet": f"No search results found for query: {query}",
                    "source": "duckduckgo"
                }]
            
            return results
            
        except requests.exceptions.RequestException as e:
            error_info = handle_request_error(e, "duckduckgo")
            return [{
                "title": f"Error: {error_info['error_type']}",
                "link": "",
                "snippet": error_info["error_message"],
                "source": "error"
            }]
            
        except Exception as e:
            logger.error(f"Unexpected error in no-API web search: {str(e)}")
            return [{
                "title": f"Error: {type(e).__name__}",
                "link": "",
                "snippet": str(e),
                "source": "error"
            }]
    
    async def _arun(
        self,
        query: str,
        num_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, str]]:
        """Run the no-API web search tool asynchronously."""
        # For simplicity, we're using the synchronous implementation
        return self._run(query, num_results, run_manager)
