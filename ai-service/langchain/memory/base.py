#!/usr/bin/env python3
"""
LangChain Memory Base Module

Defines base interfaces and abstract classes for memory management
across the TechSaaS platform. Implements the foundation for persistent
conversation history and context management.

This module is part of the TechSaaS.Tech AI service architecture,
providing memory management capabilities for the LangChain integration.
"""

import os
import logging
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

# LangChain imports
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Define placeholder classes for type hints to work without LangChain
    class BaseMessage:
        pass
    class AIMessage:
        pass
    class HumanMessage:
        pass
    class SystemMessage:
        pass

# Configure logging
logger = logging.getLogger(__name__)


class BaseMemoryManager(ABC):
    """
    Abstract base class for all memory management implementations.
    
    This interface defines the standard methods that all memory managers
    must implement, ensuring consistent conversation history management
    across different storage backends and memory strategies.
    
    Attributes:
        memory_dir: Directory for storing memory files
        memory_store: In-memory storage for conversation history
        encryption_enabled: Whether encryption is enabled for storage
    """
    
    def __init__(
        self,
        memory_dir: Optional[str] = None,
        encryption_enabled: bool = False,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize memory manager with specified configuration.
        
        Args:
            memory_dir: Directory to store memory files (default: ./memory)
            encryption_enabled: Whether to encrypt stored memories
            encryption_key: Key for encryption/decryption (required if encryption_enabled)
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available. Memory features will be limited.")
            
        self.memory_dir = memory_dir or os.path.join(os.getcwd(), "memory")
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.memory_store = {}
        self.encryption_enabled = encryption_enabled
        self.encryption_key = encryption_key
        
        if self.encryption_enabled and not self.encryption_key:
            logger.warning("Encryption enabled but no key provided. Using default key.")
            self.encryption_key = "TECHSAAS_DEFAULT_KEY"
    
    @abstractmethod
    def add_message(self, memory_key: str, message: Union[str, BaseMessage], role: Optional[str] = None) -> None:
        """
        Add a message to the specified memory context.
        
        Args:
            memory_key: Unique identifier for the memory context (typically user ID)
            message: Message content or LangChain message object
            role: Role of the message sender (human, ai, system) if message is a string
        """
        pass
    
    @abstractmethod
    def get_messages(self, memory_key: str, max_messages: Optional[int] = None) -> List[BaseMessage]:
        """
        Retrieve messages for a specific memory context.
        
        Args:
            memory_key: Unique identifier for the memory context
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of messages from the specified memory context
        """
        pass
    
    @abstractmethod
    def clear_memory(self, memory_key: Optional[str] = None) -> None:
        """
        Clear memory for a specific context or all memory.
        
        Args:
            memory_key: Specific memory context to clear, or None to clear all
        """
        pass
    
    @abstractmethod
    def save_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Save memory state to persistent storage.
        
        Args:
            memory_key: Specific memory context to save, or None to save all
            path: Path to save the memory, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def load_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Load memory state from persistent storage.
        
        Args:
            memory_key: Specific memory context to load, or None to load all
            path: Path to load the memory from, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def summarize_memory(self, 
                        memory_key: str, 
                        max_tokens: Optional[int] = None,
                        summary_model: Optional[str] = None) -> str:
        """
        Generate a summary of the conversation in a memory context.
        
        Args:
            memory_key: Memory context to summarize
            max_tokens: Maximum tokens to consider for summarization
            summary_model: Model to use for summarization (if different from main model)
            
        Returns:
            Summary of the conversation
        """
        pass
    
    @abstractmethod
    def get_memory_keys(self) -> List[str]:
        """
        Get all available memory keys.
        
        Returns:
            List of all memory keys in the system
        """
        pass
    
    @abstractmethod
    def memory_exists(self, memory_key: str) -> bool:
        """
        Check if a memory context exists.
        
        Args:
            memory_key: Memory context to check
            
        Returns:
            True if the memory exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_memory_stats(self, memory_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about memory usage.
        
        Args:
            memory_key: Specific memory context, or None for all
            
        Returns:
            Dictionary with memory statistics (e.g., message count, token usage)
        """
        pass
    
    def _get_memory_path(self, memory_key: str, custom_path: Optional[str] = None) -> str:
        """
        Get the file path for a memory file.
        
        Args:
            memory_key: Memory key to generate path for
            custom_path: Optional custom directory path
            
        Returns:
            Full path to the memory file
        """
        base_dir = custom_path or self.memory_dir
        # Sanitize memory key for use in filenames
        safe_key = "".join(c if c.isalnum() else "_" for c in memory_key)
        return os.path.join(base_dir, f"{safe_key}.json")
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt memory data for secure storage.
        
        Args:
            data: Memory data to encrypt
            
        Returns:
            Encrypted data string
        """
        # Basic implementation - in production this should use proper encryption
        if not self.encryption_enabled:
            return json.dumps(data)
            
        # Very simple encryption for demonstration - not secure for production!
        # In a real implementation, use a library like cryptography
        try:
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            # Derive key from password
            salt = b'TechSaaS_Memory_Salt'  # In production, use a secure random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            
            # Encrypt data
            f = Fernet(key)
            json_data = json.dumps(data)
            encrypted_data = f.encrypt(json_data.encode())
            return encrypted_data.decode()
            
        except ImportError:
            logger.warning("Cryptography library not available. Using base64 encoding instead.")
            import base64
            json_data = json.dumps(data)
            return base64.b64encode(json_data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt memory data from storage.
        
        Args:
            encrypted_data: Encrypted data string
            
        Returns:
            Decrypted memory data
        """
        # Basic implementation - in production this should use proper decryption
        if not self.encryption_enabled:
            return json.loads(encrypted_data)
            
        # Very simple decryption for demonstration - not secure for production!
        try:
            import base64
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            # Derive key from password
            salt = b'TechSaaS_Memory_Salt'  # Must match encryption salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            
            # Decrypt data
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted_data.encode())
            return json.loads(decrypted_data.decode())
            
        except ImportError:
            logger.warning("Cryptography library not available. Using base64 decoding instead.")
            import base64
            decoded_data = base64.b64decode(encrypted_data.encode()).decode()
            return json.loads(decoded_data)
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            return {}
