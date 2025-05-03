#!/usr/bin/env python3
"""
Simple Memory Manager

Implements a basic in-memory storage system for conversation history
as part of the TechSaaS memory management system.

This module provides a lightweight implementation of the BaseMemoryManager
interface focused on in-memory storage with optional persistence to disk.
"""

import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

from langchain.memory.base import BaseMemoryManager

# LangChain imports
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Define placeholder classes if LangChain isn't available
    class BaseMessage:
        def __init__(self, content, **kwargs):
            self.content = content
            
    class AIMessage(BaseMessage):
        pass
        
    class HumanMessage(BaseMessage):
        pass
        
    class SystemMessage(BaseMessage):
        pass

# Configure logging
logger = logging.getLogger(__name__)


class SimpleMemoryManager(BaseMemoryManager):
    """
    Simple in-memory implementation of the memory manager.
    
    This class provides a straightforward memory management system that stores
    conversation histories in memory with optional persistence to local storage.
    
    Features:
    - Fast in-memory conversation storage
    - Optional persistence to disk
    - Message type conversion
    - Basic memory statistics
    
    Example:
        ```python
        memory_manager = SimpleMemoryManager()
        
        # Add messages to a user's memory
        memory_manager.add_message("user123", "Hello, AI!", role="human")
        memory_manager.add_message("user123", "Hello, human! How can I help?", role="ai")
        
        # Retrieve messages
        messages = memory_manager.get_messages("user123")
        
        # Save to disk
        memory_manager.save_memory("user123")
        ```
    """
    
    def __init__(
        self,
        memory_dir: Optional[str] = None,
        encryption_enabled: bool = False,
        encryption_key: Optional[str] = None,
        auto_save: bool = False
    ):
        """
        Initialize the simple memory manager.
        
        Args:
            memory_dir: Directory to store memory files
            encryption_enabled: Whether to encrypt stored memories
            encryption_key: Key for encryption/decryption
            auto_save: Whether to automatically save after adding messages
        """
        super().__init__(memory_dir, encryption_enabled, encryption_key)
        self.auto_save = auto_save
        self.memory_store = {}  # Dictionary to store messages by memory key
        self.stats = {}  # Dictionary to track message statistics
    
    def add_message(self, memory_key: str, message: Union[str, BaseMessage], role: Optional[str] = None) -> None:
        """
        Add a message to the specified memory context.
        
        Args:
            memory_key: Unique identifier for the memory context
            message: Message content or LangChain message object
            role: Role of the message sender (human, ai, system) if message is a string
        """
        # Initialize memory for this key if it doesn't exist
        if memory_key not in self.memory_store:
            self.memory_store[memory_key] = []
            self.stats[memory_key] = {
                "message_count": 0,
                "last_updated": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
        
        # Convert string message to appropriate LangChain message type
        if isinstance(message, str):
            if not role:
                role = "human"  # Default role is human
                
            if role.lower() == "human":
                message_obj = HumanMessage(content=message)
            elif role.lower() == "ai":
                message_obj = AIMessage(content=message)
            elif role.lower() == "system":
                message_obj = SystemMessage(content=message)
            else:
                logger.warning(f"Unknown role '{role}', defaulting to 'human'")
                message_obj = HumanMessage(content=message)
        else:
            # Assume it's already a BaseMessage
            message_obj = message
            
        # Add message to memory
        self.memory_store[memory_key].append(message_obj)
        
        # Update stats
        self.stats[memory_key]["message_count"] = len(self.memory_store[memory_key])
        self.stats[memory_key]["last_updated"] = datetime.now().isoformat()
        
        # Auto-save if enabled
        if self.auto_save:
            self.save_memory(memory_key)
            
        logger.debug(f"Added message to memory '{memory_key}', total: {self.stats[memory_key]['message_count']}")
    
    def get_messages(self, memory_key: str, max_messages: Optional[int] = None) -> List[BaseMessage]:
        """
        Retrieve messages for a specific memory context.
        
        Args:
            memory_key: Unique identifier for the memory context
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of messages from the specified memory context
        """
        if memory_key not in self.memory_store:
            logger.warning(f"No memory found for key '{memory_key}'")
            return []
            
        messages = self.memory_store[memory_key]
        
        if max_messages is not None and max_messages > 0:
            return messages[-max_messages:]
        
        return messages
    
    def clear_memory(self, memory_key: Optional[str] = None) -> None:
        """
        Clear memory for a specific context or all memory.
        
        Args:
            memory_key: Specific memory context to clear, or None to clear all
        """
        if memory_key is None:
            logger.info("Clearing all memory")
            self.memory_store = {}
            self.stats = {}
        elif memory_key in self.memory_store:
            logger.info(f"Clearing memory for key '{memory_key}'")
            self.memory_store[memory_key] = []
            self.stats[memory_key]["message_count"] = 0
            self.stats[memory_key]["last_updated"] = datetime.now().isoformat()
        else:
            logger.warning(f"No memory found for key '{memory_key}' to clear")
    
    def save_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Save memory state to persistent storage.
        
        Args:
            memory_key: Specific memory context to save, or None to save all
            path: Path to save the memory, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if memory_key is None:
                # Save all memory contexts
                for key in self.memory_store.keys():
                    self._save_single_memory(key, path)
                return True
            else:
                # Save specific memory context
                return self._save_single_memory(memory_key, path)
                
        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
            return False
    
    def _save_single_memory(self, memory_key: str, custom_path: Optional[str] = None) -> bool:
        """
        Helper method to save a single memory context.
        
        Args:
            memory_key: Memory key to save
            custom_path: Optional custom path
            
        Returns:
            True if successful, False otherwise
        """
        if memory_key not in self.memory_store:
            logger.warning(f"No memory found for key '{memory_key}' to save")
            return False
            
        # Convert messages to serializable format
        serialized_messages = []
        for msg in self.memory_store[memory_key]:
            if hasattr(msg, 'content') and hasattr(msg, 'type'):
                serialized_messages.append({
                    "content": msg.content,
                    "type": msg.type,
                    "additional_kwargs": getattr(msg, 'additional_kwargs', {})
                })
            else:
                # Fallback if not a standard LangChain message
                serialized_messages.append({
                    "content": str(msg),
                    "type": "human",
                    "additional_kwargs": {}
                })
        
        # Prepare data structure
        memory_data = {
            "messages": serialized_messages,
            "stats": self.stats.get(memory_key, {
                "message_count": len(serialized_messages),
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            })
        }
        
        # Get file path
        file_path = self._get_memory_path(memory_key, custom_path)
        
        # Save to file (with optional encryption)
        try:
            if self.encryption_enabled:
                encrypted_data = self._encrypt_data(memory_data)
                with open(file_path, 'w') as f:
                    f.write(encrypted_data)
            else:
                with open(file_path, 'w') as f:
                    json.dump(memory_data, f, indent=2)
                    
            logger.debug(f"Saved memory '{memory_key}' to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving memory '{memory_key}' to {file_path}: {str(e)}")
            return False
    
    def load_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Load memory state from persistent storage.
        
        Args:
            memory_key: Specific memory context to load, or None to load all
            path: Path to load the memory from, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if memory_key is None:
                # Load all memory files in the directory
                base_dir = path or self.memory_dir
                loaded_count = 0
                
                for file_name in os.listdir(base_dir):
                    if file_name.endswith('.json'):
                        # Extract memory key from filename
                        key = file_name[:-5]  # Remove .json extension
                        if self._load_single_memory(key, base_dir):
                            loaded_count += 1
                            
                logger.info(f"Loaded {loaded_count} memory contexts from {base_dir}")
                return loaded_count > 0
            else:
                # Load specific memory context
                return self._load_single_memory(memory_key, path)
                
        except Exception as e:
            logger.error(f"Error loading memory: {str(e)}")
            return False
    
    def _load_single_memory(self, memory_key: str, custom_path: Optional[str] = None) -> bool:
        """
        Helper method to load a single memory context.
        
        Args:
            memory_key: Memory key to load
            custom_path: Optional custom path
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self._get_memory_path(memory_key, custom_path)
        
        if not os.path.exists(file_path):
            logger.warning(f"No memory file found at {file_path}")
            return False
            
        try:
            with open(file_path, 'r') as f:
                file_content = f.read()
                
            # Decrypt if needed
            if self.encryption_enabled:
                memory_data = self._decrypt_data(file_content)
            else:
                memory_data = json.loads(file_content)
            
            # Reconstruct messages
            messages = []
            for msg_data in memory_data.get("messages", []):
                msg_type = msg_data.get("type", "human")
                content = msg_data.get("content", "")
                
                if msg_type == "human":
                    messages.append(HumanMessage(content=content))
                elif msg_type == "ai":
                    messages.append(AIMessage(content=content))
                elif msg_type == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    messages.append(HumanMessage(content=content))
            
            # Update memory and stats
            self.memory_store[memory_key] = messages
            self.stats[memory_key] = memory_data.get("stats", {
                "message_count": len(messages),
                "last_updated": datetime.now().isoformat()
            })
            
            logger.debug(f"Loaded memory '{memory_key}' from {file_path} with {len(messages)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Error loading memory '{memory_key}' from {file_path}: {str(e)}")
            return False
    
    def summarize_memory(self, 
                        memory_key: str, 
                        max_tokens: Optional[int] = None,
                        summary_model: Optional[str] = None) -> str:
        """
        Generate a summary of the conversation in a memory context.
        
        This implementation provides a simple truncation-based summary
        since it doesn't rely on external LLM for summarization.
        
        Args:
            memory_key: Memory context to summarize
            max_tokens: Maximum tokens to consider for summarization
            summary_model: Model to use for summarization (ignored in this implementation)
            
        Returns:
            Summary of the conversation
        """
        if memory_key not in self.memory_store:
            logger.warning(f"No memory found for key '{memory_key}' to summarize")
            return "No conversation history found."
            
        messages = self.memory_store[memory_key]
        
        if not messages:
            return "No conversation history found."
            
        # Simple summary: show first message and count
        first_msg = messages[0]
        first_content = first_msg.content if hasattr(first_msg, 'content') else str(first_msg)
        
        # Truncate first message if needed
        if max_tokens and len(first_content) > max_tokens:
            first_content = first_content[:max_tokens] + "..."
            
        summary = f"Conversation with {len(messages)} messages. Started with: {first_content}"
        
        return summary
    
    def get_memory_keys(self) -> List[str]:
        """
        Get all available memory keys.
        
        Returns:
            List of all memory keys in the system
        """
        return list(self.memory_store.keys())
    
    def memory_exists(self, memory_key: str) -> bool:
        """
        Check if a memory context exists.
        
        Args:
            memory_key: Memory context to check
            
        Returns:
            True if the memory exists, False otherwise
        """
        return memory_key in self.memory_store
    
    def get_memory_stats(self, memory_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about memory usage.
        
        Args:
            memory_key: Specific memory context, or None for all
            
        Returns:
            Dictionary with memory statistics
        """
        if memory_key is None:
            # Return stats for all memory contexts
            all_stats = {
                "total_contexts": len(self.memory_store),
                "total_messages": sum(len(messages) for messages in self.memory_store.values()),
                "contexts": self.stats
            }
            return all_stats
        elif memory_key in self.stats:
            # Return stats for specific memory context
            return self.stats[memory_key]
        else:
            logger.warning(f"No memory found for key '{memory_key}' to get stats")
            return {}
