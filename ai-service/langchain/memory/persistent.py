#!/usr/bin/env python3
"""
Persistent Memory Manager

Implements a robust persistent storage system for conversation history
as part of the TechSaaS platform memory management system.

This module extends the SimpleMemoryManager with additional capabilities
for persistent storage, database integration, and advanced memory operations.
"""

import os
import logging
import json
import time
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

from langchain.memory.base import BaseMemoryManager
from langchain.memory.simple import SimpleMemoryManager

# LangChain imports
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
    from langchain_core.chat_history import BaseChatMessageHistory
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


class PersistentMemoryManager(SimpleMemoryManager):
    """
    Persistent implementation of the memory manager with database support.
    
    This class extends SimpleMemoryManager with more robust persistence options,
    including SQLite database storage, automatic summarization, and thread safety.
    
    Features:
    - SQLite database storage
    - Thread-safe operations
    - Automatic conversation summarization
    - Advanced memory operations (search, tagging)
    - Storage encryption
    - Memory backup and restore
    
    Example:
        ```python
        memory_manager = PersistentMemoryManager(
            db_path="memory.db", 
            auto_summarize=True
        )
        
        # Add messages to a user's memory
        memory_manager.add_message("user123", "Hello, AI!", role="human")
        memory_manager.add_message("user123", "Hello, human! How can I help?", role="ai")
        
        # Messages are automatically saved to the database
        
        # Retrieve messages
        messages = memory_manager.get_messages("user123")
        
        # Get a conversation summary
        summary = memory_manager.summarize_memory("user123")
        ```
    """
    
    def __init__(
        self,
        memory_dir: Optional[str] = None,
        encryption_enabled: bool = False,
        encryption_key: Optional[str] = None,
        auto_save: bool = True,
        db_path: Optional[str] = None,
        auto_summarize: bool = False,
        summarize_threshold: int = 50,
        max_memory_size: Optional[int] = 1000
    ):
        """
        Initialize the persistent memory manager.
        
        Args:
            memory_dir: Directory to store memory files
            encryption_enabled: Whether to encrypt stored memories
            encryption_key: Key for encryption/decryption
            auto_save: Whether to automatically save after adding messages
            db_path: Path to SQLite database file (default: memory.db in memory_dir)
            auto_summarize: Whether to automatically summarize long conversations
            summarize_threshold: Number of messages before triggering summarization
            max_memory_size: Maximum number of messages to store per memory context
        """
        super().__init__(memory_dir, encryption_enabled, encryption_key, auto_save)
        
        # Initialize additional attributes
        self.db_path = db_path or os.path.join(self.memory_dir, "memory.db")
        self.auto_summarize = auto_summarize
        self.summarize_threshold = summarize_threshold
        self.max_memory_size = max_memory_size
        
        # Thread safety lock
        self._lock = threading.RLock()
        
        # Initialize database if needed
        self._init_database()
        
        # Load existing memories from database
        self._load_from_database()
    
    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create memory contexts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_contexts (
                memory_key TEXT PRIMARY KEY,
                created_at TEXT,
                last_updated TEXT,
                message_count INTEGER,
                summary TEXT
            )
            ''')
            
            # Create messages table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_key TEXT,
                content TEXT,
                type TEXT,
                timestamp TEXT,
                metadata TEXT,
                FOREIGN KEY (memory_key) REFERENCES memory_contexts (memory_key)
            )
            ''')
            
            # Create tags table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_key TEXT,
                tag TEXT,
                PRIMARY KEY (memory_key, tag),
                FOREIGN KEY (memory_key) REFERENCES memory_contexts (memory_key)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Initialized memory database at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def _load_from_database(self) -> None:
        """Load existing memories from the database into memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for column name access
            cursor = conn.cursor()
            
            # Get all memory contexts
            cursor.execute('SELECT * FROM memory_contexts')
            contexts = cursor.fetchall()
            
            for context in contexts:
                memory_key = context['memory_key']
                
                # Initialize memory for this key
                if memory_key not in self.memory_store:
                    self.memory_store[memory_key] = []
                
                # Add stats
                self.stats[memory_key] = {
                    "message_count": context['message_count'],
                    "created_at": context['created_at'],
                    "last_updated": context['last_updated'],
                    "summary": context['summary']
                }
                
                # Get messages for this context
                cursor.execute(
                    'SELECT * FROM messages WHERE memory_key = ? ORDER BY id',
                    (memory_key,)
                )
                messages = cursor.fetchall()
                
                # Convert to LangChain message objects
                for msg in messages:
                    content = msg['content']
                    msg_type = msg['type']
                    metadata = json.loads(msg['metadata'] or '{}')
                    
                    if msg_type == 'human':
                        self.memory_store[memory_key].append(
                            HumanMessage(content=content, additional_kwargs=metadata)
                        )
                    elif msg_type == 'ai':
                        self.memory_store[memory_key].append(
                            AIMessage(content=content, additional_kwargs=metadata)
                        )
                    elif msg_type == 'system':
                        self.memory_store[memory_key].append(
                            SystemMessage(content=content, additional_kwargs=metadata)
                        )
            
            conn.close()
            logger.info(f"Loaded {len(contexts)} memory contexts from database")
            
        except Exception as e:
            logger.error(f"Error loading from database: {str(e)}")
    
    def add_message(self, memory_key: str, message: Union[str, BaseMessage], role: Optional[str] = None) -> None:
        """
        Add a message to the specified memory context and persist to database.
        
        Args:
            memory_key: Unique identifier for the memory context
            message: Message content or LangChain message object
            role: Role of the message sender (human, ai, system) if message is a string
        """
        with self._lock:
            # Call parent implementation to add to in-memory store
            super().add_message(memory_key, message, role)
            
            # Serialize message for database storage
            if isinstance(message, str):
                if not role:
                    role = "human"
                content = message
                msg_type = role.lower()
                metadata = {}
            else:
                content = message.content if hasattr(message, 'content') else str(message)
                if hasattr(message, 'type'):
                    msg_type = message.type
                elif isinstance(message, HumanMessage):
                    msg_type = 'human'
                elif isinstance(message, AIMessage):
                    msg_type = 'ai'
                elif isinstance(message, SystemMessage):
                    msg_type = 'system'
                else:
                    msg_type = 'unknown'
                metadata = getattr(message, 'additional_kwargs', {})
            
            # Store in database
            self._save_message_to_db(memory_key, content, msg_type, metadata)
            
            # Check if we need to summarize
            if self.auto_summarize and len(self.memory_store[memory_key]) >= self.summarize_threshold:
                self._auto_summarize_memory(memory_key)
                
            # Enforce maximum memory size if needed
            if self.max_memory_size and len(self.memory_store[memory_key]) > self.max_memory_size:
                self._trim_memory(memory_key)
    
    def _save_message_to_db(self, memory_key: str, content: str, msg_type: str, metadata: Dict) -> None:
        """
        Save a message to the database.
        
        Args:
            memory_key: Memory context key
            content: Message content
            msg_type: Message type (human, ai, system)
            metadata: Additional message metadata
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure memory context exists
            cursor.execute(
                'SELECT memory_key FROM memory_contexts WHERE memory_key = ?',
                (memory_key,)
            )
            if not cursor.fetchone():
                now = datetime.now().isoformat()
                cursor.execute(
                    'INSERT INTO memory_contexts (memory_key, created_at, last_updated, message_count, summary) VALUES (?, ?, ?, ?, ?)',
                    (memory_key, now, now, 1, '')
                )
            else:
                # Update memory context
                cursor.execute(
                    'UPDATE memory_contexts SET last_updated = ?, message_count = message_count + 1 WHERE memory_key = ?',
                    (datetime.now().isoformat(), memory_key)
                )
            
            # Insert message
            cursor.execute(
                'INSERT INTO messages (memory_key, content, type, timestamp, metadata) VALUES (?, ?, ?, ?, ?)',
                (
                    memory_key, 
                    content, 
                    msg_type, 
                    datetime.now().isoformat(),
                    json.dumps(metadata)
                )
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving message to database: {str(e)}")
    
    def _auto_summarize_memory(self, memory_key: str) -> None:
        """
        Automatically summarize a memory context when it gets too long.
        
        Args:
            memory_key: Memory context to summarize
        """
        try:
            # Get a summary
            summary = self.summarize_memory(memory_key)
            
            # Update the database with the summary
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE memory_contexts SET summary = ? WHERE memory_key = ?',
                (summary, memory_key)
            )
            conn.commit()
            conn.close()
            
            # Store in stats
            self.stats[memory_key]["summary"] = summary
            
            logger.debug(f"Auto-summarized memory '{memory_key}': {summary[:50]}...")
            
        except Exception as e:
            logger.error(f"Error auto-summarizing memory: {str(e)}")
    
    def _trim_memory(self, memory_key: str) -> None:
        """
        Trim memory to stay within maximum size limit.
        
        This method removes older messages while keeping the most recent ones.
        
        Args:
            memory_key: Memory context to trim
        """
        messages = self.memory_store[memory_key]
        
        if len(messages) <= self.max_memory_size:
            return
            
        # Keep system messages and the most recent messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        recent_messages = messages[-self.max_memory_size+len(system_messages):]
        
        # Combine system messages with recent messages
        self.memory_store[memory_key] = system_messages + [
            m for m in recent_messages if not isinstance(m, SystemMessage)
        ]
        
        # Update stats
        self.stats[memory_key]["message_count"] = len(self.memory_store[memory_key])
        
        logger.debug(f"Trimmed memory '{memory_key}' to {self.max_memory_size} messages")
    
    def clear_memory(self, memory_key: Optional[str] = None) -> None:
        """
        Clear memory for a specific context or all memory, including database.
        
        Args:
            memory_key: Specific memory context to clear, or None to clear all
        """
        with self._lock:
            # Clear in-memory storage
            super().clear_memory(memory_key)
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if memory_key is None:
                    # Clear all memory
                    cursor.execute('DELETE FROM messages')
                    cursor.execute('DELETE FROM memory_contexts')
                    cursor.execute('DELETE FROM memory_tags')
                else:
                    # Clear specific memory
                    cursor.execute('DELETE FROM messages WHERE memory_key = ?', (memory_key,))
                    cursor.execute('DELETE FROM memory_tags WHERE memory_key = ?', (memory_key,))
                    cursor.execute('DELETE FROM memory_contexts WHERE memory_key = ?', (memory_key,))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Cleared memory from database: {memory_key or 'all'}")
                
            except Exception as e:
                logger.error(f"Error clearing memory from database: {str(e)}")
    
    def summarize_memory(self, 
                         memory_key: str, 
                         max_tokens: Optional[int] = None,
                         summary_model: Optional[str] = None) -> str:
        """
        Generate a summary of the conversation in a memory context.
        
        For advanced summarization, this method can use a language model.
        Otherwise, it falls back to a basic summary like the parent class.
        
        Args:
            memory_key: Memory context to summarize
            max_tokens: Maximum tokens to consider for summarization
            summary_model: Model to use for summarization
            
        Returns:
            Summary of the conversation
        """
        if memory_key not in self.memory_store:
            logger.warning(f"No memory found for key '{memory_key}' to summarize")
            return "No conversation history found."
            
        messages = self.memory_store[memory_key]
        
        if not messages:
            return "No conversation history found."
            
        # Check if we should use an advanced summarization approach with LLM
        if LANGCHAIN_AVAILABLE and summary_model:
            try:
                from langchain_community.chat_models import ChatOllama
                from langchain_core.prompts import ChatPromptTemplate
                
                # Create a simple prompt for summarization
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Summarize the following conversation in a concise paragraph:"),
                    ("human", "{conversation}")
                ])
                
                # Format conversation for the prompt
                conversation = "\n".join([
                    f"{getattr(msg, 'type', 'human').upper()}: {getattr(msg, 'content', str(msg))}"
                    for msg in messages
                ])
                
                # Truncate if needed
                if max_tokens and len(conversation) > max_tokens:
                    conversation = conversation[:max_tokens] + "..."
                
                # Create model and chain
                model = ChatOllama(model=summary_model)
                chain = prompt | model
                
                # Generate summary
                result = chain.invoke({"conversation": conversation})
                summary = result.content if hasattr(result, 'content') else str(result)
                
                return summary
                
            except Exception as e:
                logger.error(f"Error generating LLM summary: {str(e)}")
                # Fall back to simple summary
                return super().summarize_memory(memory_key, max_tokens)
        else:
            # Use the simple summary from parent class
            return super().summarize_memory(memory_key, max_tokens)
    
    def save_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Save memory state to persistent storage (file and database).
        
        This method is used for backup purposes, as the database is 
        the primary persistent storage.
        
        Args:
            memory_key: Specific memory context to save, or None to save all
            path: Path to save the memory, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        # Database is already being kept up to date
        # This just creates additional file backups
        return super().save_memory(memory_key, path)
    
    def load_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Load memory state from persistent storage (file or database).
        
        This method is used for recovery from backup files. In normal operation,
        the database is loaded automatically at initialization.
        
        Args:
            memory_key: Specific memory context to load, or None to load all
            path: Path to load the memory from, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        if path:
            # Load from files in the specified directory
            return super().load_memory(memory_key, path)
        else:
            # Reload from database
            with self._lock:
                try:
                    if memory_key:
                        # Clear existing memory
                        if memory_key in self.memory_store:
                            self.memory_store[memory_key] = []
                        
                        # Load from database
                        conn = sqlite3.connect(self.db_path)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        
                        # Get memory context
                        cursor.execute(
                            'SELECT * FROM memory_contexts WHERE memory_key = ?',
                            (memory_key,)
                        )
                        context = cursor.fetchone()
                        
                        if not context:
                            logger.warning(f"No memory context found for '{memory_key}' in database")
                            return False
                        
                        # Add stats
                        self.stats[memory_key] = {
                            "message_count": context['message_count'],
                            "created_at": context['created_at'],
                            "last_updated": context['last_updated'],
                            "summary": context['summary']
                        }
                        
                        # Get messages
                        cursor.execute(
                            'SELECT * FROM messages WHERE memory_key = ? ORDER BY id',
                            (memory_key,)
                        )
                        messages = cursor.fetchall()
                        
                        # Convert to LangChain message objects
                        for msg in messages:
                            content = msg['content']
                            msg_type = msg['type']
                            metadata = json.loads(msg['metadata'] or '{}')
                            
                            if msg_type == 'human':
                                self.memory_store[memory_key].append(
                                    HumanMessage(content=content, additional_kwargs=metadata)
                                )
                            elif msg_type == 'ai':
                                self.memory_store[memory_key].append(
                                    AIMessage(content=content, additional_kwargs=metadata)
                                )
                            elif msg_type == 'system':
                                self.memory_store[memory_key].append(
                                    SystemMessage(content=content, additional_kwargs=metadata)
                                )
                        
                        conn.close()
                        logger.info(f"Reloaded memory '{memory_key}' from database with {len(messages)} messages")
                        return True
                    else:
                        # Reload all memories - clear and reload
                        self.memory_store = {}
                        self.stats = {}
                        self._load_from_database()
                        return True
                        
                except Exception as e:
                    logger.error(f"Error reloading from database: {str(e)}")
                    return False
    
    def get_memory_keys(self) -> List[str]:
        """
        Get all available memory keys from database.
        
        Returns:
            List of all memory keys in the system
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT memory_key FROM memory_contexts')
            keys = [row[0] for row in cursor.fetchall()]
            conn.close()
            return keys
        except Exception as e:
            logger.error(f"Error getting memory keys from database: {str(e)}")
            return super().get_memory_keys()
    
    def memory_exists(self, memory_key: str) -> bool:
        """
        Check if a memory context exists in database.
        
        Args:
            memory_key: Memory context to check
            
        Returns:
            True if the memory exists, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT memory_key FROM memory_contexts WHERE memory_key = ?',
                (memory_key,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"Error checking memory existence in database: {str(e)}")
            return super().memory_exists(memory_key)
    
    def get_memory_stats(self, memory_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about memory usage from database.
        
        Args:
            memory_key: Specific memory context, or None for all
            
        Returns:
            Dictionary with memory statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if memory_key:
                cursor.execute(
                    'SELECT * FROM memory_contexts WHERE memory_key = ?',
                    (memory_key,)
                )
                context = cursor.fetchone()
                
                if not context:
                    conn.close()
                    return {}
                
                stats = {
                    "message_count": context[3],
                    "created_at": context[1],
                    "last_updated": context[2],
                    "summary": context[4]
                }
                
                # Get tag info
                cursor.execute(
                    'SELECT tag FROM memory_tags WHERE memory_key = ?',
                    (memory_key,)
                )
                tags = [row[0] for row in cursor.fetchall()]
                stats["tags"] = tags
                
                conn.close()
                return stats
            else:
                # Get overall stats
                cursor.execute('SELECT COUNT(*) FROM memory_contexts')
                context_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM messages')
                message_count = cursor.fetchone()[0]
                
                # Calculate average messages per context
                avg_messages = message_count / context_count if context_count > 0 else 0
                
                # Get top contexts by message count
                cursor.execute(
                    'SELECT memory_key, message_count FROM memory_contexts ORDER BY message_count DESC LIMIT 5'
                )
                top_contexts = [(row[0], row[1]) for row in cursor.fetchall()]
                
                stats = {
                    "total_contexts": context_count,
                    "total_messages": message_count,
                    "avg_messages_per_context": avg_messages,
                    "top_contexts": dict(top_contexts)
                }
                
                conn.close()
                return stats
                
        except Exception as e:
            logger.error(f"Error getting memory stats from database: {str(e)}")
            return super().get_memory_stats(memory_key)
    
    def add_memory_tag(self, memory_key: str, tag: str) -> bool:
        """
        Add a tag to a memory context for categorization.
        
        Args:
            memory_key: Memory context to tag
            tag: Tag to add
            
        Returns:
            True if successful, False otherwise
        """
        if not self.memory_exists(memory_key):
            logger.warning(f"Cannot add tag to non-existent memory: {memory_key}")
            return False
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Add tag (will fail silently if tag already exists due to PRIMARY KEY constraint)
            cursor.execute(
                'INSERT OR IGNORE INTO memory_tags (memory_key, tag) VALUES (?, ?)',
                (memory_key, tag)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error adding memory tag: {str(e)}")
            return False
    
    def remove_memory_tag(self, memory_key: str, tag: str) -> bool:
        """
        Remove a tag from a memory context.
        
        Args:
            memory_key: Memory context to remove tag from
            tag: Tag to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM memory_tags WHERE memory_key = ? AND tag = ?',
                (memory_key, tag)
            )
            
            conn.commit()
            conn.close()
            
            # Return true if a row was deleted
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error removing memory tag: {str(e)}")
            return False
    
    def get_memories_by_tag(self, tag: str) -> List[str]:
        """
        Get all memory keys that have a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of memory keys with the specified tag
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT memory_key FROM memory_tags WHERE tag = ?',
                (tag,)
            )
            
            keys = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return keys
            
        except Exception as e:
            logger.error(f"Error getting memories by tag: {str(e)}")
            return []
    
    def search_memories(self, query: str) -> List[Tuple[str, float]]:
        """
        Search for memories containing the query text.
        
        This is a simple content-based search implementation.
        
        Args:
            query: Text to search for
            
        Returns:
            List of (memory_key, relevance_score) tuples
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple SQLite full-text search
            cursor.execute(
                '''
                SELECT memory_key, COUNT(*) as count
                FROM messages 
                WHERE content LIKE ?
                GROUP BY memory_key
                ORDER BY count DESC
                ''',
                (f'%{query}%',)
            )
            
            results = [(row[0], row[1]) for row in cursor.fetchall()]
            conn.close()
            
            # Normalize scores
            max_score = max([score for _, score in results]) if results else 1
            normalized_results = [(key, score/max_score) for key, score in results]
            
            return normalized_results
            
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            return []
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        Create a backup of the memory database.
        
        Args:
            backup_path: Path for the backup file, or None to use default
            
        Returns:
            True if successful, False otherwise
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                self.memory_dir, 
                f"memory_backup_{timestamp}.db"
            )
            
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Created memory database backup at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {str(e)}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore memory database from a backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
            
        try:
            # Close any open connections
            self.memory_store = {}
            self.stats = {}
            
            # Copy backup over current database
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            # Reload from database
            self._load_from_database()
            
            logger.info(f"Restored memory database from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restoring database: {str(e)}")
            return False
