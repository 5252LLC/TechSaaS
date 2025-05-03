#!/usr/bin/env python3
"""
LangChainService

Core service class for interacting with language models through LangChain.
Provides a unified interface for model management, chain creation, and response generation.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Union, Any, Callable
from pathlib import Path
import time
from datetime import datetime

# LangChain imports
try:
    from langchain_core.language_models import BaseChatModel, BaseLanguageModel
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough, RunnableSequence
    from langchain_community.chat_models import ChatOllama
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    
    LANGCHAIN_AVAILABLE = True
except (ImportError, AttributeError) as e:
    LANGCHAIN_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"LangChain dependencies not available: {str(e)}")

# Local imports
try:
    from langchain.memory.simple import SimpleMemoryManager
    from langchain.memory.persistent import PersistentMemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Memory management modules not available. Using basic memory functionality.")

# Configure logging
logger = logging.getLogger(__name__)


class LangChainService:
    """
    Primary service class for interacting with language models through LangChain.
    
    This class simplifies working with language models by providing:
    - Easy model initialization and switching
    - Template management for different tasks
    - Chain creation and execution
    - Memory management for conversations
    - Response generation with various options
    """
    
    DEFAULT_MODELS = {
        "llama3": "llama3:8b",
        "phi3": "phi3:mini",
        "gemma": "gemma:7b",
        "mistral": "mistral:7b",
        "vicuna": "vicuna:13b",
        "llava": "llava:13b",
        "default": "llama3:8b"
    }
    
    def __init__(
            self, 
            model_name: Optional[str] = None,
            ollama_base_url: Optional[str] = None,
            model_kwargs: Optional[Dict[str, Any]] = None,
            templates_dir: Optional[str] = None,
            memory_dir: Optional[str] = None,
            persistent_memory: bool = False,
            encryption_enabled: bool = False,
            encryption_key: Optional[str] = None
        ):
        """
        Initialize the LangChain service.
        
        Args:
            model_name: Name of the model to use (default: llama3:8b)
            ollama_base_url: Base URL for Ollama API (default: http://localhost:11434)
            model_kwargs: Additional arguments to pass to the model
            templates_dir: Directory containing prompt templates
            memory_dir: Directory for storing memory files
            persistent_memory: Whether to use persistent memory storage
            encryption_enabled: Whether to encrypt stored memories
            encryption_key: Key for encryption/decryption
        """
        # Check if LangChain is available
        if not LANGCHAIN_AVAILABLE:
            logger.error("LangChain dependencies are required for this service.")
            raise ImportError(
                "LangChain dependencies are required. "
                "Install with pip install langchain-community langchain-core"
            )
            
        self.ollama_base_url = ollama_base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = model_name or self.DEFAULT_MODELS["default"]
        self.model_kwargs = model_kwargs or {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_ctx": 4096,
            "repeat_penalty": 1.1
        }
        
        # Initialize templates
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "prompts"
        )
        self.templates = self._load_templates()
        
        # Initialize model
        try:
            self.model = self._init_model()
        except Exception as e:
            logger.error(f"Error initializing model {self.model_name}: {str(e)}")
            # Create a placeholder model for testing
            self.model = None
        
        # Initialize chains registry
        self.chains = {}
        
        # Initialize memory manager
        memory_path = memory_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory"
        )
        
        if MEMORY_AVAILABLE and persistent_memory:
            logger.info("Initializing persistent memory manager")
            self.memory_manager = PersistentMemoryManager(
                memory_dir=memory_path,
                encryption_enabled=encryption_enabled,
                encryption_key=encryption_key,
                auto_save=True,
                auto_summarize=True
            )
        elif MEMORY_AVAILABLE:
            logger.info("Initializing simple memory manager")
            self.memory_manager = SimpleMemoryManager(
                memory_dir=memory_path,
                encryption_enabled=encryption_enabled,
                encryption_key=encryption_key
            )
        else:
            logger.warning("Memory modules not available, using basic dictionary storage")
            self.memory_manager = None
            # Initialize basic memory dictionary as fallback
            self.memory = {}
        
        logger.info(f"Initialized LangChainService with model {self.model_name}")
    
    def _init_model(self) -> BaseChatModel:
        """
        Initialize the language model.
        
        Returns:
            Initialized language model
        """
        try:
            model = ChatOllama(
                model=self.model_name,
                base_url=self.ollama_base_url,
                **self.model_kwargs
            )
            return model
        except Exception as e:
            logger.error(f"Error initializing model {self.model_name}: {str(e)}")
            raise
    
    def _load_templates(self) -> Dict[str, Any]:
        """
        Load prompt templates from files.
        
        Returns:
            Dictionary of templates
        """
        templates = {}
        templates_path = Path(self.templates_dir)
        
        if not templates_path.exists():
            logger.warning(f"Templates directory {self.templates_dir} not found")
            return templates
        
        try:
            # Load JSON templates
            for file_path in templates_path.glob("*.json"):
                with open(file_path, "r") as f:
                    template_data = json.load(f)
                    template_name = file_path.stem
                    templates[template_name] = template_data
            
            # Load text templates
            for file_path in templates_path.glob("*.txt"):
                with open(file_path, "r") as f:
                    template_content = f.read()
                    template_name = file_path.stem
                    templates[template_name] = template_content
                    
            logger.info(f"Loaded {len(templates)} templates from {self.templates_dir}")
            return templates
            
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            return {}
    
    def switch_model(self, model_name: str, **model_kwargs) -> bool:
        """
        Switch to a different model.
        
        Args:
            model_name: Name of the model to switch to
            **model_kwargs: Additional arguments for the model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update model name and kwargs
            self.model_name = model_name
            if model_kwargs:
                self.model_kwargs.update(model_kwargs)
            
            # Reinitialize the model
            self.model = self._init_model()
            
            # Clear existing chains to force recreation with new model
            self.chains = {}
            
            logger.info(f"Switched to model {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching to model {model_name}: {str(e)}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get a list of available models.
        
        Returns:
            List of available model names
        """
        return list(self.DEFAULT_MODELS.keys())
        
    def create_chain(
            self, 
            template_name: str,
            system_message: Optional[str] = None,
            memory_key: Optional[str] = None,
            output_parser: Optional[Callable] = None,
            **kwargs
        ) -> RunnableSequence:
        """
        Create a LangChain chain using a template.
        
        Args:
            template_name: Name of the template to use
            system_message: Optional system message to override template default
            memory_key: Key to store/retrieve memory for this chain
            output_parser: Optional output parser to process model response
            **kwargs: Additional arguments for chain configuration
            
        Returns:
            RunnableSequence chain
        """
        if not self.model:
            logger.error("No model available. Chain creation failed.")
            raise ValueError("No model available. Initialize or switch to a valid model.")
            
        # Get template content
        template_content = self.templates.get(template_name)
        if not template_content:
            logger.error(f"Template {template_name} not found")
            raise ValueError(f"Template {template_name} not found in templates directory")
        
        # Use system message from template or provided one
        if isinstance(template_content, dict) and "system" in template_content:
            system_prompt = template_content["system"]
        else:
            system_prompt = system_message or template_content
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # Set up memory if requested
        if memory_key:
            # Initialize memory if needed
            if self.memory_manager:
                # Use memory manager
                if not self.memory_manager.memory_exists(memory_key):
                    # Add a system message if available
                    if system_prompt:
                        self.memory_manager.add_message(memory_key, system_prompt, role="system")
                
                def get_history():
                    return self.memory_manager.get_messages(memory_key)
                
            else:
                # Fallback to basic memory dictionary
                if memory_key not in self.memory:
                    self.memory[memory_key] = []
                    # Add a system message if available
                    if system_prompt:
                        self.memory[memory_key].append(SystemMessage(content=system_prompt))
                
                def get_history():
                    return self.memory[memory_key]
                
            # Create chain with memory
            history_chain = RunnablePassthrough.assign(
                history=lambda _: get_history()
            )
            chain = history_chain | prompt | self.model
        else:
            # No memory chain
            chain = prompt | self.model
        
        # Add output parser if provided
        if output_parser:
            chain = chain | output_parser
        else:
            chain = chain | StrOutputParser()
        
        # Store chain in registry for reuse
        self.chains[template_name] = chain
        
        return chain
    
    def generate_response(
            self,
            input_text: str,
            template_name: Optional[str] = None,
            memory_key: Optional[str] = None,
            system_message: Optional[str] = None,
            stream: bool = False,
            **kwargs
        ) -> Union[str, Any]:
        """
        Generate a response using a chain.
        
        Args:
            input_text: Input text for the model
            template_name: Name of the template to use
            memory_key: Key to store/retrieve memory for this chain
            system_message: Optional system message to override template
            stream: Whether to stream the response
            **kwargs: Additional arguments for chain execution
            
        Returns:
            Generated response as string or streaming response
        """
        if not self.model:
            logger.error("No model available. Response generation failed.")
            raise ValueError("No model available. Initialize or switch to a valid model.")
        
        # Get or create chain
        chain = None
        chain_key = template_name or "default"
        
        if chain_key in self.chains:
            chain = self.chains[chain_key]
        elif template_name:
            chain = self.create_chain(
                template_name=template_name,
                system_message=system_message,
                memory_key=memory_key,
                **kwargs
            )
        else:
            # Create a simple chain without template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message or "You are a helpful assistant."),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}")
            ])
            
            if memory_key:
                # Initialize memory if needed
                if self.memory_manager:
                    # Use memory manager
                    if not self.memory_manager.memory_exists(memory_key):
                        # Add a system message if available
                        if system_message:
                            self.memory_manager.add_message(memory_key, system_message, role="system")
                    
                    def get_history():
                        return self.memory_manager.get_messages(memory_key)
                    
                else:
                    # Fallback to basic memory dictionary
                    if memory_key not in self.memory:
                        self.memory[memory_key] = []
                        # Add a system message if available
                        if system_message:
                            self.memory[memory_key].append(SystemMessage(content=system_message))
                    
                    def get_history():
                        return self.memory[memory_key]
                
                # Create chain with memory
                history_chain = RunnablePassthrough.assign(
                    history=lambda _: get_history()
                )
                chain = history_chain | prompt | self.model | StrOutputParser()
            else:
                # No memory chain
                chain = prompt | self.model | StrOutputParser()
            
            self.chains[chain_key] = chain
        
        # Run chain
        start_time = time.time()
        try:
            # Process input data
            input_data = {"input": input_text}
            input_data.update(kwargs)
            
            # Generate response
            if stream:
                return chain.stream(input_data)
            else:
                response = chain.invoke(input_data)
                
                # Add to memory if memory key is provided
                if memory_key:
                    if self.memory_manager:
                        # Add to memory manager
                        self.memory_manager.add_message(memory_key, input_text, role="human")
                        self.memory_manager.add_message(memory_key, response, role="ai")
                    else:
                        # Add to basic memory dictionary
                        self.memory[memory_key].append(HumanMessage(content=input_text))
                        self.memory[memory_key].append(AIMessage(content=response))
                
                end_time = time.time()
                logger.debug(f"Response generated in {end_time - start_time:.2f}s")
                return response
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def clear_memory(self, memory_key: Optional[str] = None) -> None:
        """
        Clear memory for a specific key or all memory.
        
        Args:
            memory_key: Memory key to clear, or None to clear all memory
        """
        if self.memory_manager:
            # Use memory manager
            self.memory_manager.clear_memory(memory_key)
        else:
            # Fallback to basic memory dictionary
            if memory_key:
                if memory_key in self.memory:
                    self.memory[memory_key] = []
                    logger.debug(f"Cleared memory for {memory_key}")
            else:
                self.memory = {}
                logger.debug("Cleared all memory")
    
    def get_memory(self, memory_key: str, max_messages: Optional[int] = None) -> List[Any]:
        """
        Get messages from a specific memory context.
        
        Args:
            memory_key: Memory key to retrieve
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of messages from the specified memory context
        """
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.get_messages(memory_key, max_messages)
        else:
            # Fallback to basic memory dictionary
            if memory_key in self.memory:
                messages = self.memory[memory_key]
                if max_messages:
                    return messages[-max_messages:]
                return messages
            return []
    
    def save_memory(self, memory_key: Optional[str] = None, path: Optional[str] = None) -> bool:
        """
        Save memory state to persistent storage.
        
        Args:
            memory_key: Specific memory context to save, or None to save all
            path: Path to save the memory, or None to use default location
            
        Returns:
            True if successful, False otherwise
        """
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.save_memory(memory_key, path)
        else:
            # Fallback - not supported with basic memory dictionary
            logger.warning("Memory persistence not available with basic memory storage")
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
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.load_memory(memory_key, path)
        else:
            # Fallback - not supported with basic memory dictionary
            logger.warning("Memory persistence not available with basic memory storage")
            return False
    
    def summarize_memory(self, memory_key: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate a summary of the conversation in a memory context.
        
        Args:
            memory_key: Memory context to summarize
            max_tokens: Maximum tokens to consider for summarization
            
        Returns:
            Summary of the conversation
        """
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.summarize_memory(
                memory_key, 
                max_tokens,
                summary_model=self.model_name
            )
        else:
            # Fallback to basic memory summary
            if memory_key in self.memory:
                messages = self.memory[memory_key]
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
            else:
                return "No conversation history found."
    
    def get_memory_stats(self, memory_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about memory usage.
        
        Args:
            memory_key: Specific memory context, or None for all
            
        Returns:
            Dictionary with memory statistics
        """
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.get_memory_stats(memory_key)
        else:
            # Fallback to basic statistics
            if memory_key:
                if memory_key in self.memory:
                    return {
                        "message_count": len(self.memory[memory_key]),
                        "last_updated": datetime.now().isoformat()
                    }
                return {}
            else:
                return {
                    "total_contexts": len(self.memory),
                    "total_messages": sum(len(msgs) for msgs in self.memory.values())
                }
    
    def get_memory_keys(self) -> List[str]:
        """
        Get all available memory keys.
        
        Returns:
            List of all memory keys in the system
        """
        if self.memory_manager:
            # Use memory manager
            return self.memory_manager.get_memory_keys()
        else:
            # Fallback to basic memory dictionary
            return list(self.memory.keys())
