#!/usr/bin/env python3
"""
TechSaaS LangChain Integration

This package provides LangChain integration for the TechSaaS platform,
with support for model management, prompting, and memory persistence.

Features:
- Model integration with Ollama
- Prompt template management
- Chain creation and execution
- Memory management with persistence
- Conversation summarization
"""

from langchain.service import LangChainService

# Make memory packages available
try:
    from langchain.memory import (
        BaseMemoryManager,
        SimpleMemoryManager,
        PersistentMemoryManager
    )
    __all__ = [
        'LangChainService',
        'BaseMemoryManager',
        'SimpleMemoryManager',
        'PersistentMemoryManager'
    ]
except ImportError:
    __all__ = ['LangChainService']
