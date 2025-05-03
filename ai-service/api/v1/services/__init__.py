"""
Services for the AI API
This module provides service classes that handle business logic for the AI API
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AIService(ABC):
    """
    Abstract base class for AI services
    
    Provides a common interface for different AI service implementations
    """
    
    @abstractmethod
    def analyze(self, content, task="summarize", model=None, options=None):
        """
        Analyze content using AI
        
        Args:
            content (str): Content to analyze
            task (str): Type of analysis to perform
            model (str, optional): Model to use
            options (dict, optional): Additional options
            
        Returns:
            dict: Analysis results
        """
        pass
    
    @abstractmethod
    def chat(self, message, history=None, model=None, options=None):
        """
        Generate a response to a chat message
        
        Args:
            message (str): User message
            history (list, optional): Chat history
            model (str, optional): Model to use
            options (dict, optional): Additional options
            
        Returns:
            dict: Chat response
        """
        pass
    
    @abstractmethod
    def complete(self, prompt, max_tokens=None, temperature=None, model=None, options=None):
        """
        Generate a text completion
        
        Args:
            prompt (str): Completion prompt
            max_tokens (int, optional): Maximum tokens to generate
            temperature (float, optional): Temperature parameter
            model (str, optional): Model to use
            options (dict, optional): Additional options
            
        Returns:
            dict: Completion result
        """
        pass
