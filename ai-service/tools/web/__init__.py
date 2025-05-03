"""
Web tools for LangChain integration.

This package provides tools for web search, content extraction, and related web functionality
that can be used by LangChain agents.
"""

from .search import WebSearchTool, NoAPIWebSearchTool
from .extraction import WebContentExtractionTool, StructuredContentExtractionTool
from .utils import handle_request_error, extract_main_content, is_valid_url, create_user_agent

__all__ = [
    'WebSearchTool',
    'NoAPIWebSearchTool',
    'WebContentExtractionTool',
    'StructuredContentExtractionTool',
    'handle_request_error',
    'extract_main_content',
    'is_valid_url',
    'create_user_agent',
]
