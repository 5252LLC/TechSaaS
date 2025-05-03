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
    
    # Import LangChain globals for debugging configuration
    import langchain_core
    
    LANGCHAIN_AVAILABLE = True
except (ImportError, AttributeError) as e:
    LANGCHAIN_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"LangChain dependencies not available: {str(e)}")

# Local imports
try:
    from langchain.memory.simple import SimpleMemoryManager
    from langchain.memory.persistent import PersistentMemoryManager
    from langchain.compat import use_debug_mode, get_debug_mode, memory_adapter, clear_memory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Memory management modules not available. Using basic memory functionality.")
    
    # Try to import at least the compatibility functions
    try:
        from langchain.compat import use_debug_mode, get_debug_mode, memory_adapter, clear_memory
    except ImportError:
        logger.warning("Compatibility layer not available. Some features will be limited.")
        
        # Define stub functions if not available
        def use_debug_mode(enable=True): return False
        def get_debug_mode(): return False
        def memory_adapter(service): return getattr(service, "memory", {})
        def clear_memory(service, key=None): return False

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
        
        # Initialize internal memory storage
        self._memory = {}
        
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
        
        logger.info(f"Initialized LangChainService with model {self.model_name}")

    def _init_model(self) -> BaseChatModel:
        """Initialize the language model."""
        try:
            if not LANGCHAIN_AVAILABLE:
                logger.error("LangChain dependencies not available. Cannot initialize model.")
                return None
                
            # Set verbose mode for models
            verbose = os.environ.get("LANGCHAIN_VERBOSE", "false").lower() == "true"
            
            # Initialize the model
            if self.model_name.lower().startswith("ollama/"):
                # Extract the model name without the 'ollama/' prefix
                model_name_without_prefix = self.model_name[len("ollama/"):]
                
                # Configure Ollama
                model = ChatOllama(
                    model=model_name_without_prefix,
                    temperature=self.model_kwargs.get("temperature", 0.7),
                    verbose=verbose,
                    base_url=self.ollama_base_url
                )
                
                logger.info(f"Initialized Ollama model: {model_name_without_prefix}")
                return model
            else:
                # Default to Ollama model
                logger.warning(f"Unknown model provider for {self.model_name}, defaulting to Ollama")
                return ChatOllama(
                    model=self.model_name,
                    temperature=self.model_kwargs.get("temperature", 0.7),
                    verbose=verbose,
                    base_url=self.ollama_base_url
                )
        except Exception as e:
            logger.exception(f"Failed to initialize model: {str(e)}")
            raise

    def set_verbose(self, verbose: bool) -> None:
        """
        Set verbosity level for the language model.
        
        Args:
            verbose: Whether to enable verbose logging
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, cannot set verbose mode")
            return
        
        try:
            # Use compatibility layer
            use_debug_mode(verbose)
            
            # Also set model-specific verbosity if possible
            if self.model and hasattr(self.model, "verbose"):
                self.model.verbose = verbose
        except Exception as e:
            logger.warning(f"Error setting verbose mode: {str(e)}")

    def get_verbose(self) -> bool:
        """
        Get current verbosity level.
        
        Returns:
            bool: Current verbosity setting
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, cannot get verbose mode")
            return False
        
        try:
            # Use compatibility layer
            return get_debug_mode()
        except Exception as e:
            logger.warning(f"Error getting verbose mode: {str(e)}")
            return False

    @property
    def memory(self) -> dict:
        """
        Provide a compatible interface to memory regardless of storage method.
        
        This property ensures backward compatibility with code expecting a 
        direct memory attribute.
        
        Returns:
            dict: Memory storage dictionary
        """
        # For testing compatibility, we prioritize the internal _memory
        if hasattr(self, "_memory"):
            return self._memory
        
        # Use compatibility layer as fallback
        return memory_adapter(self)

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
            system_message: Optional[str] = None,
            memory_key: Optional[str] = None,
            chain_type: str = "basic",
            chain_key: Optional[str] = None,
            stream: bool = False,
            **kwargs
        ) -> str:
        """Generate a response from the language model."""
        if not LANGCHAIN_AVAILABLE:
            return "LangChain dependencies not available. Cannot generate response."
            
        if not self.model and not chain_key:
            return "No language model initialized."
            
        # Use existing chain if provided
        if chain_key and chain_key in self.chains:
            chain = self.chains[chain_key]
        else:
            # Create a new chain
            chain_key = chain_key or f"chain_{int(time.time())}"
            
            # Create prompt based on chain type
            if chain_type == "chat":
                if system_message:
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", system_message),
                        MessagesPlaceholder(variable_name="history"),
                        ("human", "{input}")
                    ])
                else:
                    prompt = ChatPromptTemplate.from_messages([
                        MessagesPlaceholder(variable_name="history"),
                        ("human", "{input}")
                    ])
            else:
                # Basic prompt
                template = "{input}"
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_message) if system_message else None,
                    ("human", template)
                ])
            
            # Memory handling
            if memory_key:
                if self.memory_manager:
                    # Use memory manager for history
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
            
            # Set debug mode for LangChain callbacks
            original_debug = langchain_core.get_debug()
            try:
                # Temporarily disable debug to avoid callback errors
                langchain_core.set_debug(False)
                
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
            finally:
                # Restore original debug setting
                langchain_core.set_debug(original_debug)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"

    def clear_memory(self, memory_key: Optional[str] = None) -> bool:
        """
        Clear conversation memory.
        
        Args:
            memory_key: Optional key to clear specific conversation memory.
                       If None, clears all memory.
        
        Returns:
            bool: Success status
        """
        logger.info(f"Clearing memory{'.' if memory_key is None else f' for key: {memory_key}'}")
        
        # First, clear internal memory dictionary for test compatibility
        if hasattr(self, "_memory"):
            if memory_key:
                if memory_key in self._memory:
                    self._memory[memory_key] = []
                else:
                    logger.warning(f"No memory found for key '{memory_key}' to clear")
            else:
                self._memory.clear()
        
        # If we have a memory manager, use it
        if self.memory_manager:
            try:
                if memory_key:
                    self.memory_manager.clear_memory(memory_key)
                else:
                    self.memory_manager.clear_all_memory()
                return True
            except Exception as e:
                logger.error(f"Error clearing memory: {str(e)}")
                return False
        
        return True

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
            bool: True if successful, False otherwise
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
            bool: True if successful, False otherwise
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

    def analyze(self, text: str, analysis_type: str = "summarize", model: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze text using AI models
        
        Args:
            text (str): The text content to analyze
            analysis_type (str): The type of analysis to perform (summarize, sentiment, etc.)
            model (str, optional): The model to use for analysis
            options (Dict[str, Any], optional): Additional options for the analysis
            
        Returns:
            Dict[str, Any]: The analysis results
        """
        logger.info(f"Analyzing text with analysis_type={analysis_type}, model={model or self.model_name}")
        
        # Initialize options dictionary if None
        options = options or {}
        
        # Set up model
        llm = self._get_chat_model(model)
        
        # Track prompt and completion tokens
        start_time = time.time()
        input_tokens = self._estimate_tokens(text)
        
        # Define analysis prompts for different types
        analysis_prompts = {
            "summarize": "Summarize the following text:\n\n{text}",
            "sentiment": "Analyze the sentiment of the following text and classify it as positive, negative, or neutral. Include a score between -1 and 1, where -1 is very negative, 0 is neutral, and 1 is very positive. Also include details about what contributes to this sentiment:\n\n{text}",
            "extract": "Extract the key entities, people, organizations, locations, and important information from the following text:\n\n{text}",
            "categorize": "Categorize the following text into appropriate topics or themes:\n\n{text}",
            "language": "Identify the language of the following text and provide its ISO language code:\n\n{text}"
        }
        
        # Get appropriate prompt or use default
        prompt_template = analysis_prompts.get(
            analysis_type, 
            f"Perform {analysis_type} analysis on the following text:\n\n{{text}}"
        )
        
        try:
            # Create and run the prompt
            prompt = PromptTemplate.from_template(prompt_template)
            chain = prompt | llm | StrOutputParser()
            result = chain.invoke({"text": text})
            
            # Format result based on analysis type
            formatted_result = self._format_analysis_result(result, analysis_type, options)
            
            # Calculate tokens
            completion_tokens = self._estimate_tokens(result)
            total_tokens = input_tokens + completion_tokens
            
            # Create response
            response = {
                "result": formatted_result,
                "analysis_type": analysis_type,
                "model": model or self.model_name,
                "processing_time": time.time() - start_time,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            return response
        except Exception as e:
            logger.exception(f"Error in analyze: {str(e)}")
            return {
                "result": f"Error analyzing text: {str(e)}",
                "error": True,
                "analysis_type": analysis_type,
                "model": model or self.model_name
            }
    
    def _format_analysis_result(self, result: str, analysis_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the analysis result based on the analysis type
        
        Args:
            result (str): The raw analysis result
            analysis_type (str): The type of analysis performed
            options (Dict[str, Any]): Analysis options
            
        Returns:
            Dict[str, Any]: Formatted analysis result
        """
        detailed = options.get("detailed", False)
        
        if analysis_type == "sentiment":
            # Try to extract sentiment and score from text
            if "positive" in result.lower():
                sentiment = "positive"
                score = 0.7  # Default positive score
            elif "negative" in result.lower():
                sentiment = "negative"
                score = -0.7  # Default negative score
            else:
                sentiment = "neutral"
                score = 0.0
                
            # Try to extract numerical score if present
            import re
            score_match = re.search(r'score:?\s*([-+]?\d*\.\d+|\d+)', result, re.IGNORECASE)
            if score_match:
                try:
                    score = float(score_match.group(1))
                except ValueError:
                    pass
                
            response = {
                "sentiment": sentiment,
                "score": score,
                "text": result if detailed else None
            }
            
            if detailed:
                response["details"] = {
                    "positivity": max(0, (score + 1) / 2),
                    "negativity": max(0, (1 - score) / 2),
                    "neutrality": 1 - abs(score)
                }
                
            return response
        elif analysis_type == "summarize":
            return {
                "summary": result,
                "length": len(result)
            }
        elif analysis_type == "extract":
            return {
                "entities": result,
                "raw": result if detailed else None
            }
        else:
            # Default formatting for other analysis types
            return {
                "result": result,
                "type": analysis_type
            }
            
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, conversation_id: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024, **kwargs) -> Dict[str, Any]:
        """
        Generate chat responses using AI models
        
        Args:
            messages (List[Dict[str, str]]): List of message dictionaries with 'role' and 'content'
            model (str, optional): The model to use for chat
            conversation_id (str, optional): ID for tracking conversation history
            temperature (float): Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens (int): Maximum number of tokens to generate
            **kwargs: Additional parameters for the chat
            
        Returns:
            Dict[str, Any]: The chat response
        """
        logger.info(f"Generating chat response with model={model or self.model_name}, conversation_id={conversation_id}")
        
        # Set up model with parameters
        llm = self._get_chat_model(
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Track tokens and time
        start_time = time.time()
        input_tokens = sum(self._estimate_tokens(msg["content"]) for msg in messages)
        
        try:
            # Convert message format to LangChain format
            langchain_messages = []
            for msg in messages:
                role = msg["role"].lower()
                content = msg["content"]
                
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
            
            # Generate response
            response = llm.invoke(langchain_messages)
            response_text = response.content
            
            # Estimate tokens in response
            completion_tokens = self._estimate_tokens(response_text)
            total_tokens = input_tokens + completion_tokens
            
            # Format response in OpenAI-like format for consistency
            formatted_response = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model or self.model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            # Save to memory if conversation_id is provided
            if conversation_id:
                self._save_to_memory(conversation_id, messages, response_text)
            
            return formatted_response
        except Exception as e:
            logger.exception(f"Error in chat: {str(e)}")
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "model": model or self.model_name,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": f"I apologize, but I encountered an error: {str(e)}"
                        },
                        "finish_reason": "error"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": 0,
                    "total_tokens": input_tokens
                },
                "error": True
            }
    
    def complete(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024, **kwargs) -> Dict[str, Any]:
        """
        Generate text completions using AI models
        
        Args:
            prompt (str): The text prompt to complete
            model (str, optional): The model to use for completion
            temperature (float): Controls randomness (0.0 = deterministic, 1.0 = creative)
            max_tokens (int): Maximum number of tokens to generate
            **kwargs: Additional parameters for the completion
            
        Returns:
            Dict[str, Any]: The completion response
        """
        logger.info(f"Generating text completion with model={model or self.model_name}")
        
        # Set up model with parameters
        llm = self._get_chat_model(
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Track tokens and time
        start_time = time.time()
        input_tokens = self._estimate_tokens(prompt)
        
        try:
            # Create completion chain
            completion_prompt = PromptTemplate.from_template("{prompt}")
            chain = completion_prompt | llm | StrOutputParser()
            
            # Generate completion
            result = chain.invoke({"prompt": prompt})
            
            # Estimate tokens in response
            completion_tokens = self._estimate_tokens(result)
            total_tokens = input_tokens + completion_tokens
            
            # Format response in OpenAI-like format for consistency
            formatted_response = {
                "id": f"cmpl-{int(time.time())}",
                "object": "text.completion",
                "created": int(time.time()),
                "model": model or self.model_name,
                "choices": [
                    {
                        "text": result,
                        "index": 0,
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            }
            
            return formatted_response
        except Exception as e:
            logger.exception(f"Error in complete: {str(e)}")
            return {
                "id": f"cmpl-{int(time.time())}",
                "model": model or self.model_name,
                "choices": [
                    {
                        "text": f"Error: {str(e)}",
                        "index": 0,
                        "finish_reason": "error"
                    }
                ],
                "usage": {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": 0,
                    "total_tokens": input_tokens
                },
                "error": True
            }
    
    def list_models(self) -> Dict[str, Any]:
        """
        List available AI models with their capabilities
        
        Returns:
            Dict[str, Any]: List of available models and their metadata
        """
        logger.info("Listing available AI models")
        
        try:
            # In a real implementation, this would dynamically discover models
            # For now, we'll return a static list
            models = [
                {
                    "id": "llama2",
                    "name": "Llama 2",
                    "provider": "ollama",
                    "capabilities": ["chat", "completion", "analysis"],
                    "context_window": 4096,
                    "tier": "basic"
                },
                {
                    "id": "mistral",
                    "name": "Mistral 7B",
                    "provider": "ollama",
                    "capabilities": ["chat", "completion", "analysis"],
                    "context_window": 8192,
                    "tier": "pro"
                },
                {
                    "id": "codellama",
                    "name": "CodeLlama",
                    "provider": "ollama",
                    "capabilities": ["chat", "completion", "code"],
                    "context_window": 16384,
                    "tier": "pro"
                }
            ]
            
            return {
                "models": models,
                "default_model": self.model_name,
                "count": len(models)
            }
        except Exception as e:
            logger.exception(f"Error in list_models: {str(e)}")
            return {
                "models": [],
                "default_model": self.model_name,
                "count": 0,
                "error": str(e)
            }
    
    def _get_chat_model(self, model_name: Optional[str] = None, **kwargs) -> Any:
        """
        Get a configured chat model
        
        Args:
            model_name (str, optional): The model name to use
            **kwargs: Additional parameters for the model
            
        Returns:
            Any: The configured chat model
        """
        # Default to instance model name if none provided
        model_name = model_name or self.model_name
        
        # If model name has a provider prefix (e.g., ollama/llama2), extract just the model name
        if '/' in model_name:
            model_name = model_name.split('/')[1]
        
        # Set up model parameters with defaults
        model_kwargs = {
            'temperature': kwargs.get('temperature', self.model_kwargs.get('temperature', 0.7)),
            'max_tokens': kwargs.get('max_tokens', self.model_kwargs.get('max_tokens', 1024))
        }
        
        # Add any additional parameters from kwargs, skipping internal ones
        for key, value in kwargs.items():
            if key not in ['temperature', 'max_tokens', 'verbose']:
                model_kwargs[key] = value
        
        # Set verbose mode based on instance attribute to ensure compatibility
        # but avoid passing it directly to avoid deprecated attribute errors
        verbose_mode = getattr(self, 'verbose', False)
        
        # Create and return the model - ensure no verbose parameter is passed
        try:
            # Temporarily ensure debug mode is disabled during model creation
            original_debug = None
            try:
                if hasattr(langchain_core, 'get_debug'):
                    original_debug = langchain_core.get_debug()
                    langchain_core.set_debug(verbose_mode)
            except (ImportError, AttributeError):
                pass
                
            # Create the chat model without direct verbose parameter
            model = ChatOllama(
                model=model_name,
                base_url=self.ollama_base_url,
                **model_kwargs
            )
            
            # Restore original debug mode if needed
            if original_debug is not None:
                try:
                    langchain_core.set_debug(original_debug)
                except:
                    pass
                    
            return model
            
        except Exception as e:
            logger.exception(f"Failed to create chat model: {str(e)}")
            # Use a fallback if available
            if hasattr(self, 'fallback_model'):
                logger.warning(f"Using fallback model: {self.fallback_model}")
                return self.fallback_model
            raise

    def _save_to_memory(self, conversation_id: str, messages: List[Dict[str, str]], response: str) -> None:
        """
        Save conversation messages to memory
        
        Args:
            conversation_id (str): ID for tracking conversation history
            messages (List[Dict[str, str]]): List of message dictionaries
            response (str): AI response to save
            
        Returns:
            None
        """
        try:
            # Get or create memory manager
            if self.memory_manager:
                # Add the new user message (last message in the list)
                user_messages = [m for m in messages if m["role"].lower() == "user"]
                if user_messages:
                    last_user_message = user_messages[-1]["content"]
                    self.memory_manager.add_user_message(conversation_id, last_user_message)
                
                # Add the AI response
                self.memory_manager.add_ai_message(conversation_id, response)
                logger.debug(f"Saved conversation to memory, conversation_id={conversation_id}")
            else:
                logger.warning("No memory manager available, conversation not saved")
        except Exception as e:
            logger.exception(f"Error saving to memory: {str(e)}")
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text
        
        Args:
            text (str): The text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        if not text:
            return 0
            
        # Simple estimation: ~4 characters per token (rough approximation)
        return len(text) // 4 + 1

    def enable_caching(self) -> None:
        """
        Enable caching for LangChain operations
        """
        try:
            # Set local flag for caching
            self.caching_enabled = True
            logger.info("LangChain caching enabled")
            
            # Additional caching setup would go here
            # For example, setting up Redis or SQLite caching for LangChain
            
        except Exception as e:
            logger.exception(f"Error enabling LangChain caching: {str(e)}")
    
    def is_caching_enabled(self) -> bool:
        """
        Check if caching is enabled
        
        Returns:
            bool: True if caching is enabled, False otherwise
        """
        return getattr(self, 'caching_enabled', False)
    
    def is_persistent_memory(self) -> bool:
        """
        Check if persistent memory is enabled
        
        Returns:
            bool: True if persistent memory is enabled, False otherwise
        """
        return self.persistent_memory

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
