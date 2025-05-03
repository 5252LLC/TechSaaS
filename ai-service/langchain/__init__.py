"""
LangChain Components

This package provides the core LangChain components for the TechSaaS platform:
- LangChainService: Main service for interacting with LLMs via LangChain
- Template management for different tasks
- Memory management for conversations
- Chain creation and optimization
"""

from .service import LangChainService

__all__ = ["LangChainService"]
