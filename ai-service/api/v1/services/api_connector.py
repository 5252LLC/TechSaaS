"""
API Connector Framework
Provides standardized interfaces for connecting to various AI API providers
with comprehensive security controls
"""

import logging
import json
import time
import re
from abc import ABC, abstractmethod
import requests
from flask import current_app

# Setup logger
logger = logging.getLogger(__name__)

class SecurityFilter:
    """
    Security filter for sanitizing API requests and responses
    Implements protection against prompt injection, malicious content, etc.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.blocked_patterns = [
            r"system:\s*",
            r"<(?:/?(?:system|admin|sudo|exec|function|script))>",
            r"function\s*\(",
            r"exec\s*\(",
            r"fetch\s*\(",
            # Add more patterns as needed
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.blocked_patterns]
        
    def sanitize_request(self, request_data):
        """
        Sanitize outgoing request to protect external API
        
        Args:
            request_data (dict): Request data to be sanitized
            
        Returns:
            dict: Sanitized request data
            bool: True if request is safe, False if potentially malicious
        """
        # Deep copy to avoid modifying original
        clean_data = json.loads(json.dumps(request_data))
        
        # Check for prompt injection or malicious content
        is_safe = True
        
        # Sanitize text fields
        if 'prompt' in clean_data:
            clean_data['prompt'], prompt_safe = self._sanitize_text(clean_data['prompt'])
            is_safe = is_safe and prompt_safe
            
        if 'messages' in clean_data and isinstance(clean_data['messages'], list):
            for i, msg in enumerate(clean_data['messages']):
                if 'content' in msg and isinstance(msg['content'], str):
                    clean_data['messages'][i]['content'], msg_safe = self._sanitize_text(msg['content'])
                    is_safe = is_safe and msg_safe
        
        return clean_data, is_safe
        
    def sanitize_response(self, response_data):
        """
        Sanitize incoming response to protect the application
        
        Args:
            response_data (dict): Response data to be sanitized
            
        Returns:
            dict: Sanitized response data
        """
        # Deep copy to avoid modifying original
        clean_data = json.loads(json.dumps(response_data))
        
        # Sanitize text fields
        if 'choices' in clean_data and isinstance(clean_data['choices'], list):
            for i, choice in enumerate(clean_data['choices']):
                if 'text' in choice:
                    clean_data['choices'][i]['text'], _ = self._sanitize_text(choice['text'])
                elif 'message' in choice and 'content' in choice['message']:
                    clean_data['choices'][i]['message']['content'], _ = self._sanitize_text(
                        choice['message']['content']
                    )
        
        if 'content' in clean_data:
            clean_data['content'], _ = self._sanitize_text(clean_data['content'])
            
        return clean_data
    
    def _sanitize_text(self, text):
        """
        Sanitize text content
        
        Args:
            text (str): Text to sanitize
            
        Returns:
            str: Sanitized text
            bool: True if text is safe, False if potentially malicious
        """
        if not isinstance(text, str):
            return text, True
            
        # Check for malicious patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                logger.warning(f"Potentially malicious content detected: {text[:50]}...")
                return text, False
                
        # Implement other sanitization as needed
        
        return text, True


class RateLimiter:
    """
    Rate limiter for API requests based on subscription tier
    """
    
    def __init__(self):
        self.request_counts = {}
        self.tier_limits = {
            "basic": 100,    # requests per minute
            "pro": 500,      # requests per minute
            "enterprise": 2000  # requests per minute
        }
    
    def check_rate_limit(self, user_id, tier="basic"):
        """
        Check if a user has exceeded their rate limit
        
        Args:
            user_id (str): User identifier
            tier (str): Subscription tier (basic, pro, enterprise)
            
        Returns:
            bool: True if within rate limit, False if exceeded
        """
        current_minute = int(time.time() / 60)
        
        if user_id not in self.request_counts:
            self.request_counts[user_id] = {}
            
        if current_minute not in self.request_counts[user_id]:
            # Clean up old entries
            self.request_counts[user_id] = {current_minute: 1}
            return True
            
        # Check if user has exceeded their tier's rate limit
        if self.request_counts[user_id][current_minute] >= self.tier_limits.get(tier, 100):
            return False
            
        # Increment the request count
        self.request_counts[user_id][current_minute] += 1
        return True


class APIConnector(ABC):
    """
    Abstract base class for AI API connectors
    """
    
    def __init__(self, api_key=None, config=None):
        self.api_key = api_key or current_app.config.get('DEFAULT_API_KEY')
        self.config = config or {}
        self.security_filter = SecurityFilter()
        self.rate_limiter = RateLimiter()
    
    @abstractmethod
    def generate_text(self, prompt, options=None):
        """
        Generate text based on a prompt
        
        Args:
            prompt (str): Text prompt
            options (dict): Generation options
            
        Returns:
            dict: Generated text and metadata
        """
        pass
    
    @abstractmethod
    def chat_completion(self, messages, options=None):
        """
        Generate a chat completion
        
        Args:
            messages (list): List of message dictionaries with 'role' and 'content'
            options (dict): Generation options
            
        Returns:
            dict: Chat completion response
        """
        pass
    
    @abstractmethod
    def embed_text(self, text, options=None):
        """
        Generate embeddings for text
        
        Args:
            text (str): Text to embed
            options (dict): Embedding options
            
        Returns:
            dict: Embedding vectors and metadata
        """
        pass
        

class OpenAIConnector(APIConnector):
    """
    Connector for OpenAI API
    """
    
    def __init__(self, api_key=None, config=None):
        super().__init__(api_key, config)
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
    
    def generate_text(self, prompt, options=None):
        """Generate text using OpenAI Completions API"""
        options = options or {}
        
        # Prepare request data
        request_data = {
            'model': options.get('model', self.default_model),
            'prompt': prompt,
            'max_tokens': options.get('max_tokens', 1000),
            'temperature': options.get('temperature', 0.7)
        }
        
        # Apply security filters
        filtered_data, is_safe = self.security_filter.sanitize_request(request_data)
        
        if not is_safe:
            logger.warning("Potentially unsafe request blocked")
            return {"error": "Request contains potentially unsafe content"}
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=filtered_data,
                timeout=30
            )
            
            response_data = response.json()
            
            # Sanitize response
            sanitized_response = self.security_filter.sanitize_response(response_data)
            
            return sanitized_response
            
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}
    
    def chat_completion(self, messages, options=None):
        """Generate chat completion using OpenAI Chat API"""
        options = options or {}
        
        # Prepare request data
        request_data = {
            'model': options.get('model', self.default_model),
            'messages': messages,
            'max_tokens': options.get('max_tokens', 1000),
            'temperature': options.get('temperature', 0.7)
        }
        
        # Apply security filters
        filtered_data, is_safe = self.security_filter.sanitize_request(request_data)
        
        if not is_safe:
            logger.warning("Potentially unsafe request blocked")
            return {"error": "Request contains potentially unsafe content"}
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=filtered_data,
                timeout=30
            )
            
            response_data = response.json()
            
            # Sanitize response
            sanitized_response = self.security_filter.sanitize_response(response_data)
            
            return sanitized_response
            
        except Exception as e:
            logger.exception(f"Error calling OpenAI API: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}
    
    def embed_text(self, text, options=None):
        """Generate embeddings using OpenAI Embeddings API"""
        options = options or {}
        
        # Prepare request data
        request_data = {
            'model': options.get('model', 'text-embedding-ada-002'),
            'input': text
        }
        
        # Apply security filters
        filtered_data, is_safe = self.security_filter.sanitize_request(request_data)
        
        if not is_safe:
            logger.warning("Potentially unsafe request blocked")
            return {"error": "Request contains potentially unsafe content"}
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=filtered_data,
                timeout=30
            )
            
            response_data = response.json()
            
            # No need to sanitize embeddings (numeric vectors)
            
            return response_data
            
        except Exception as e:
            logger.exception(f"Error calling OpenAI Embeddings API: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}


class APIConnectorFactory:
    """
    Factory for creating API connector instances
    """
    
    @staticmethod
    def create_connector(provider, api_key=None, config=None):
        """
        Create an API connector for the specified provider
        
        Args:
            provider (str): API provider name (e.g., 'openai', 'anthropic', 'custom')
            api_key (str): API key for the provider
            config (dict): Configuration options
            
        Returns:
            APIConnector: An instance of the appropriate connector
        """
        config = config or {}
        
        if provider.lower() == 'openai':
            return OpenAIConnector(api_key, config)
        # Add more providers as needed
        else:
            raise ValueError(f"Unsupported API provider: {provider}")
