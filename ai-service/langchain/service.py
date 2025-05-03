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
            templates_dir: Optional[str] = None
        ):
        """
        Initialize the LangChain service.
        
        Args:
            model_name: Name of the model to use (default: llama3:8b)
            ollama_base_url: Base URL for Ollama API (default: http://localhost:11434)
            model_kwargs: Additional arguments to pass to the model
            templates_dir: Directory containing prompt templates
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
        
        # Initialize memory
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
            if memory_key not in self.memory:
                self.memory[memory_key] = []
            
            def get_history():
                return self.memory[memory_key]
                
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
                if memory_key not in self.memory:
                    self.memory[memory_key] = []
                
                def get_history():
                    return self.memory[memory_key]
                    
                history_chain = RunnablePassthrough.assign(
                    history=lambda _: get_history()
                )
                chain = history_chain | prompt | self.model | StrOutputParser()
            else:
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
        if memory_key:
            if memory_key in self.memory:
                self.memory[memory_key] = []
                logger.debug(f"Cleared memory for {memory_key}")
        else:
            self.memory = {}
            logger.debug("Cleared all memory")
