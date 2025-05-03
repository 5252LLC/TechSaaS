#!/usr/bin/env python3
"""
LangChain Memory Management Package

This package implements persistent conversation memory for the LangChain service,
enabling user-specific context maintenance across sessions for the TechSaaS platform.

Features:
- Per-user conversation history storage
- Persistent memory across sessions
- Memory summarization for long conversations
- Multiple storage backend support
- Memory encryption for secure storage
"""

from langchain.memory.base import BaseMemoryManager
from langchain.memory.simple import SimpleMemoryManager
from langchain.memory.persistent import PersistentMemoryManager

__all__ = [
    'BaseMemoryManager',
    'SimpleMemoryManager',
    'PersistentMemoryManager'
]