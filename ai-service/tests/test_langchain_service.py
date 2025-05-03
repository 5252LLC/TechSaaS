#!/usr/bin/env python3
"""
Test LangChain Service

Tests the functionality of the LangChainService class.
"""

import unittest
import os
import sys
import logging
from unittest.mock import MagicMock, patch
from typing import Dict, List, Optional, Any

# Add the parent directory to the Python path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger("LangChainServiceTest")


class TestLangChainService(unittest.TestCase):
    """Test cases for the LangChainService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Apply patches
        self.patchers = []
        
        # Patch langchain modules
        import_patcher = patch.dict('sys.modules', {
            'langchain_core.language_models': MagicMock(),
            'langchain_core.chat_history': MagicMock(),
            'langchain_core.prompts': MagicMock(),
            'langchain_core.output_parsers': MagicMock(),
            'langchain_core.runnables': MagicMock(),
            'langchain_community.chat_models': MagicMock(),
            'langchain_core.messages': MagicMock()
        })
        import_patcher.start()
        self.patchers.append(import_patcher)
        
        # Now import the service
        from langchain.service import LangChainService
        
        # Create a mock model
        self.mock_model = MagicMock()
        self.mock_model.invoke.return_value = "Mock response"
        
        # Create a mock chain
        self.mock_chain = MagicMock()
        self.mock_chain.invoke.return_value = "Chain response"
        self.mock_chain.stream.return_value = ["Streaming", "response"]
        
        # Create the service with mocked components
        self.service = LangChainService(
            model_name="test-model",
            ollama_base_url="http://test-url:11434"
        )
        
        # Replace internal objects with mocks
        self.service.model = self.mock_model
        self.service._init_model = MagicMock(return_value=self.mock_model)
        self.service.create_chain = MagicMock(return_value=self.mock_chain)
        
        # Add test templates
        self.service.templates = {
            "test_template": "You are a test assistant. Be concise and helpful.",
            "crypto_analysis": "Analyze the following cryptocurrency data: {input}"
        }
    
    def tearDown(self):
        """Clean up after tests."""
        for patcher in self.patchers:
            patcher.stop()
    
    def test_initialization(self):
        """Test that LangChainService initializes correctly."""
        self.assertEqual(self.service.model_name, "test-model")
        self.assertEqual(self.service.ollama_base_url, "http://test-url:11434")
        self.assertIsNotNone(self.service.model_kwargs)
        self.assertIsNotNone(self.service.templates)
        self.assertIsNotNone(self.service.model)
        self.assertEqual(len(self.service.chains), 0)
        self.assertEqual(len(self.service.memory), 0)
    
    def test_get_available_models(self):
        """Test getting available models."""
        models = self.service.get_available_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
    
    def test_switch_model(self):
        """Test switching models."""
        # Switch to a new model
        result = self.service.switch_model("new-model", temperature=0.5)
        
        # Verify that the model was switched
        self.assertTrue(result)
        self.assertEqual(self.service.model_name, "new-model")
        self.assertEqual(self.service.model_kwargs["temperature"], 0.5)
        
        # Verify that the chains were reset
        self.assertEqual(len(self.service.chains), 0)
    
    def test_generate_response(self):
        """Test generating responses."""
        # Generate a response
        response = self.service.generate_response(
            input_text="Hello, world!",
            template_name="test_template"
        )
        
        # Verify response
        self.assertEqual(response, "Chain response")
        
        # Verify create_chain was called with correct arguments
        self.service.create_chain.assert_called_with(
            template_name="test_template",
            system_message=None,
            memory_key=None
        )
        
        # Initialize memory for test
        self.service.memory = {"test-memory": []}
        
        # Test with memory key
        response = self.service.generate_response(
            input_text="Remember this",
            template_name="test_template",
            memory_key="test-memory"
        )
        
        # Verify create_chain was called with memory key
        self.service.create_chain.assert_called_with(
            template_name="test_template",
            system_message=None,
            memory_key="test-memory"
        )
        
        # Test streaming response
        result = self.service.generate_response(
            input_text="Stream response",
            template_name="test_template",
            stream=True
        )
        
        # Test should pass if this doesn't raise exceptions
        self.assertEqual(self.mock_chain.stream.call_count, 1)
    
    def test_clear_memory(self):
        """Test memory clearing."""
        # Setup test memory
        self.service.memory = {
            "memory1": ["message1", "message2"],
            "memory2": ["message3"]
        }
        
        # Test clearing specific memory
        self.service.clear_memory("memory1")
        self.assertEqual(self.service.memory["memory1"], [])
        self.assertEqual(self.service.memory["memory2"], ["message3"])
        
        # Test clearing all memory
        self.service.clear_memory()
        self.assertEqual(self.service.memory, {})


if __name__ == "__main__":
    logger.info("Running LangChainService tests...")
    unittest.main()
