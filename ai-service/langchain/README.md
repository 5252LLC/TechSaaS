# TechSaaS LangChain Service

This module provides a compatibility layer and service wrapper for LangChain integration in the TechSaaS platform.

## Overview

The LangChain service provides a unified interface for interacting with language models through LangChain, abstracting away the complexities of model management, chain creation, and response generation.

## Key Components

### LangChainService

Core service class for interacting with language models. Provides methods for:

- Chat conversations with memory persistence
- Text completion with configurable parameters
- Text analysis with various analysis types
- Memory management for conversation history
- Model switching and management

### Compatibility Layer

The `compat.py` module provides compatibility functions for handling LangChain version differences, including:

- Monkey patching for deprecated attributes
- Version-agnostic functions for debug mode settings
- Seamless bridging between older and newer LangChain APIs

## Usage

### Basic Usage

```python
from langchain.service import LangChainService

# Initialize service
service = LangChainService(
    model_name="ollama/llama2",
    ollama_base_url="http://localhost:11434",
    persistent_memory=True
)

# Chat with conversation history
response = service.chat(
    messages=[{"role": "user", "content": "Hello!"}],
    conversation_id="user-123"
)

# Text analysis
analysis = service.analyze(
    text="This is a test document to analyze.",
    analysis_type="summarize"
)

# Text completion
completion = service.complete(
    prompt="Write a function to calculate factorial in Python:",
    max_tokens=500
)
```

### Using the Compatibility Layer

```python
from langchain.compat import use_debug_mode, get_debug_mode

# Set debug mode in a version-agnostic way
use_debug_mode(True)

# Check current debug mode
is_debug = get_debug_mode()
```

## Configuration

The service can be configured with the following environment variables:

- `OLLAMA_BASE_URL`: Base URL for the Ollama service (default: http://localhost:11434)
- `DEFAULT_AI_MODEL`: Default AI model to use (default: ollama/llama2)
- `LANGCHAIN_VERBOSE`: Enable verbose logging for LangChain (default: False)
- `MEMORY_DIR`: Directory for persistent memory storage (default: /tmp/techsaas-memory)

## Monetization Support

The service includes features to support the TechSaaS monetization strategy:

- Token usage tracking for pay-per-use billing
- Model capability information for tier-based access control
- Performance metrics for system monitoring

## Error Handling

The service provides graceful error handling and fallbacks:

- Automatically retries on transient errors
- Falls back to simpler models when preferred models are unavailable
- Provides detailed error information for debugging

## Development Notes

When extending this service, follow these guidelines:

1. Always use the compatibility layer for version-sensitive features
2. Add new methods to the LangChainService class instead of creating separate utilities
3. Include proper token tracking for monetization
4. Implement appropriate error handling and logging
