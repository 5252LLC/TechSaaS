"""
Tests for AI endpoint routes in the Flask API

These tests verify that the AI endpoints correctly handle requests,
validate input, and return appropriate responses.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask
from api.app import create_app
from api.v1.schemas import (
    AnalyzeRequestSchema,
    ChatRequestSchema,
    CompletionRequestSchema
)

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = create_app(config_name='test')
    
    # Override config settings for testing
    app.config.update({
        'TESTING': True,
        'OLLAMA_BASE_URL': 'http://mock-ollama:11434',
        'DEFAULT_AI_MODEL': 'mock-model',
        'CACHE_TYPE': 'SimpleCache',  # Use in-memory cache for testing
        'DEFAULT_MAX_TOKENS': 1024,
        'DEFAULT_TEMPERATURE': 0.7
    })
    
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def mock_langchain_service():
    """Mock the LangChain service for testing."""
    with patch('api.v1.services.langchain_factory.get_langchain_service') as mock:
        service = MagicMock()
        
        # Setup mock response for chat method
        chat_response = {
            "id": "chat-12345",
            "model": "mock-model",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is a mock response from the AI assistant."
                    },
                    "finish_reason": "stop",
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        }
        service.chat.return_value = chat_response
        
        # Setup mock response for completion method
        completion_response = {
            "id": "cmpl-12345",
            "model": "mock-model",
            "choices": [
                {
                    "text": "This is a mock completion response.",
                    "finish_reason": "stop",
                    "index": 0
                }
            ],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 7,
                "total_tokens": 12
            }
        }
        service.complete.return_value = completion_response
        
        # Setup mock response for analysis method
        analysis_response = {
            "id": "ana-12345",
            "analysis_type": "sentiment",
            "model": "mock-model",
            "result": {
                "sentiment": "positive",
                "score": 0.85,
                "details": {
                    "positivity": 0.85,
                    "negativity": 0.05,
                    "neutrality": 0.10
                }
            },
            "usage": {
                "input_tokens": 8,
                "output_tokens": 12,
                "total_tokens": 20
            }
        }
        service.analyze.return_value = analysis_response
        
        mock.return_value = service
        yield service

def test_chat_endpoint_valid_request(client, mock_langchain_service):
    """Test that the chat endpoint accepts valid requests."""
    data = {
        "message": "Hello, how are you?",
        "history": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ],
        "model": "mock-model",
        "options": {"temperature": 0.7}
    }
    
    response = client.post(
        '/api/v1/ai/chat',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "response" in response_data
    assert "model_used" in response_data
    assert response_data["model_used"] == "mock-model"

    # Verify service was called with correct parameters
    mock_langchain_service.chat.assert_called_once()
    args, kwargs = mock_langchain_service.chat.call_args
    assert "messages" in kwargs
    assert kwargs["messages"] == data["history"] + [{"role": "user", "content": data["message"]}]
    assert "model" in kwargs
    assert kwargs["model"] == "mock-model"

def test_chat_endpoint_invalid_request(client):
    """Test that the chat endpoint rejects invalid requests."""
    # Missing required message field
    data = {
        "model": "mock-model",
        "options": {"temperature": 0.7}
    }
    
    response = client.post(
        '/api/v1/ai/chat',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "errors" in response_data

def test_completion_endpoint_valid_request(client, mock_langchain_service):
    """Test that the completion endpoint accepts valid requests."""
    data = {
        "prompt": "Write a poem about AI:",
        "max_tokens": 100,
        "temperature": 0.7,
        "model": "mock-model"
    }
    
    response = client.post(
        '/api/v1/ai/completion',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "completion" in response_data
    assert "model_used" in response_data
    assert "tokens_used" in response_data
    assert response_data["model_used"] == "mock-model"

    # Verify service was called with correct parameters
    mock_langchain_service.complete.assert_called_once()
    args, kwargs = mock_langchain_service.complete.call_args
    assert "prompt" in kwargs
    assert kwargs["prompt"] == data["prompt"]
    assert "model" in kwargs
    assert kwargs["model"] == "mock-model"

def test_completion_endpoint_invalid_request(client):
    """Test that the completion endpoint rejects invalid requests."""
    # Missing required prompt field
    data = {
        "model": "mock-model",
        "temperature": 0.7
    }
    
    response = client.post(
        '/api/v1/ai/completion',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "errors" in response_data

def test_analyze_endpoint_valid_request(client, mock_langchain_service):
    """Test that the analyze endpoint accepts valid requests."""
    data = {
        "content": "I love this product! It works perfectly.",
        "task": "sentiment",
        "model": "mock-model",
        "options": {"detailed": True}
    }
    
    response = client.post(
        '/api/v1/ai/analyze',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "task" in response_data
    assert "result" in response_data
    assert "model_used" in response_data
    assert response_data["task"] == "sentiment"
    assert response_data["model_used"] == "mock-model"

    # Verify service was called with correct parameters
    mock_langchain_service.analyze.assert_called_once()
    args, kwargs = mock_langchain_service.analyze.call_args
    assert "text" in kwargs
    assert kwargs["text"] == data["content"]
    assert "analysis_type" in kwargs
    assert kwargs["analysis_type"] == "sentiment"
    assert "model" in kwargs
    assert kwargs["model"] == "mock-model"

def test_analyze_endpoint_invalid_request(client):
    """Test that the analyze endpoint rejects invalid requests."""
    # Missing required content field
    data = {
        "task": "sentiment",
        "model": "mock-model"
    }
    
    response = client.post(
        '/api/v1/ai/analyze',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "errors" in response_data

def test_example_beginner_endpoint(client):
    """Test that the beginner example endpoint returns helpful information."""
    response = client.get('/api/v1/ai/example/beginner')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "examples" in response_data
    assert "explanation" in response_data
    assert len(response_data["examples"]) > 0
