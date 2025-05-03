# AI Service Implementation Guide - Intermediate Level

This guide explains key implementation details of the TechSaaS AI service for intermediate developers. It focuses on practical approaches to solve common challenges when working with LangChain, implementing API monetization, and testing AI components.

## Contents
1. [Implementing a LangChain Compatibility Layer](#implementing-a-langchain-compatibility-layer)
2. [Setting Up Usage Tracking for API Monetization](#setting-up-usage-tracking-for-api-monetization)
3. [Testing AI Endpoints Effectively](#testing-ai-endpoints-effectively)
4. [Integrating Multiple Model Providers](#integrating-multiple-model-providers)

## Implementing a LangChain Compatibility Layer

When working with rapidly evolving libraries like LangChain, maintaining compatibility across versions becomes crucial. Our compatibility layer solves this with a pragmatic approach:

```python
# Example from langchain/compat.py

def get_llm_model_name(llm):
    """Get model name from an LLM regardless of LangChain version."""
    try:
        # Modern LangChain version
        if hasattr(llm, "model_name"):
            return llm.model_name
        # Legacy version
        elif hasattr(llm, "model"):
            return llm.model
        # Fallback for custom LLMs
        else:
            return str(llm.__class__.__name__)
    except Exception as e:
        logger.warning(f"Could not extract model name: {e}")
        return "unknown"
```

This function exemplifies our approach to version-agnostic code. When implementing your own compatibility layer:

1. Use feature detection (`hasattr`) rather than version checking
2. Implement fallbacks for missing attributes
3. Handle exceptions gracefully with informative logging
4. Provide a standardized return format

Here's how to build your own compatibility layer for any rapidly evolving library:

```python
# Step 1: Create a version detection function
def detect_library_version():
    try:
        import your_library
        version = getattr(your_library, "__version__", "0.0.0")
        major, minor, patch = map(int, version.split("."))
        return major, minor, patch
    except (ImportError, ValueError):
        return 0, 0, 0

# Step 2: Create wrapper functions for commonly used features
def get_feature_x(obj):
    """Get feature X regardless of library version."""
    # Try new API first
    if hasattr(obj, "feature_x_new_name"):
        return obj.feature_x_new_name
    # Fall back to old API
    elif hasattr(obj, "feature_x_old_name"):
        return obj.feature_x_old_name
    # Provide fallback implementation if needed
    else:
        return default_implementation()

# Step 3: Apply monkey patching if necessary
def apply_patches():
    major, minor, _ = detect_library_version()
    
    if major < 1:
        # Apply patches for older versions
        import your_library
        
        if not hasattr(your_library.SomeClass, "new_method"):
            your_library.SomeClass.new_method = lambda self, *args, **kwargs: legacy_implementation(self, *args, **kwargs)
```

## Setting Up Usage Tracking for API Monetization

To monetize your API, accurate usage tracking is essential. Here's how we implemented it:

```python
# Usage tracking helper functions

def calculate_tokens(text, model_id=None):
    """Calculate approximate token count for billing."""
    if not text:
        return 0
    # Approximate token count (4 chars ≈ 1 token)
    return len(text) // 4

def record_usage(user_id, endpoint, input_text, output_text, model_id=None):
    """Record API usage for billing purposes."""
    tokens_input = calculate_tokens(input_text)
    tokens_output = calculate_tokens(output_text)
    
    # Add to database
    usage = APIUsage(
        user_id=user_id,
        endpoint=endpoint,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        model_id=model_id,
        billable=True
    )
    db.session.add(usage)
    db.session.commit()
    
    return {
        'tokens_input': tokens_input,
        'tokens_output': tokens_output,
        'total_tokens': tokens_input + tokens_output
    }
```

This implementation:
1. Provides approximate token counting for billing
2. Records usage data in a structured format
3. Returns usage metrics for API responses
4. Associates usage with specific users and endpoints

To implement this in your own project:

1. Create a database model for tracking usage:
```python
class APIUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    endpoint = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Add additional fields as needed for your billing model
```

2. Add middleware to capture usage metrics:
```python
@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    # Only track API requests
    if request.path.startswith('/api/'):
        duration = time.time() - g.start_time
        
        # Create usage record
        usage = APIUsage(
            user_id=get_user_id(),
            endpoint=request.path,
            duration=duration,
            # Add additional metrics
        )
        
        db.session.add(usage)
        db.session.commit()
    
    return response
```

3. Implement functions to calculate specific metrics for your API:
```python
def calculate_billable_units(request_data, response_data):
    """Calculate billable units based on request/response."""
    # Implement your billing logic here
    pass
```

## Testing AI Endpoints Effectively

Testing AI endpoints requires a blend of unit testing and integration testing:

```python
# Example test for the /api/v1/ai/chat endpoint

def test_chat_endpoint():
    """Test the chat endpoint with a simple query."""
    client = app.test_client()
    
    # Test data
    payload = {
        "message": "Hello, how are you?",
        "conversation_id": "test-conversation",
        "model": "ollama/llama2"
    }
    
    # Make request with test API key
    response = client.post(
        "/api/v1/ai/chat",
        json=payload,
        headers={"X-API-Key": "test-api-key"}
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json
    assert "response" in data
    assert len(data["response"]) > 0
    assert "usage" in data
    assert data["usage"]["total_tokens"] > 0
```

When writing tests for AI endpoints:
1. Use a test client to simulate HTTP requests
2. Include all required parameters in test payloads
3. Test with valid and invalid inputs
4. Verify response structure and content
5. Check usage tracking metrics

For more robust AI endpoint testing:

```python
# Test with different models
def test_chat_with_different_models():
    client = app.test_client()
    models = ["ollama/llama2", "ollama/mistral"]
    
    for model in models:
        payload = {
            "message": "Hello, how are you?",
            "model": model
        }
        
        response = client.post(
            "/api/v1/ai/chat",
            json=payload,
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        assert "response" in response.json

# Test error handling
def test_chat_with_invalid_input():
    client = app.test_client()
    
    # Empty message
    payload = {
        "message": "",
        "model": "ollama/llama2"
    }
    
    response = client.post(
        "/api/v1/ai/chat",
        json=payload,
        headers={"X-API-Key": "test-api-key"}
    )
    
    assert response.status_code == 400
    assert "error" in response.json
```

## Integrating Multiple Model Providers

Our AI service supports multiple model providers through a factory pattern:

```python
def create_language_model(model_id=None, provider=None, **kwargs):
    """Create a language model instance based on model_id or provider."""
    if not model_id and not provider:
        model_id = current_app.config.get('DEFAULT_LLM_MODEL', 'ollama/llama2')
    
    # Extract provider from model_id if not explicitly provided
    if model_id and not provider:
        provider = extract_provider_from_model_id(model_id)
    
    # Get the appropriate provider-specific factory
    if provider == 'ollama':
        return create_ollama_llm(model_id, **kwargs)
    elif provider == 'openai':
        return create_openai_llm(model_id, **kwargs)
    elif provider == 'huggingface':
        return create_huggingface_llm(model_id, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
```

To add support for a new provider:

1. Create a provider-specific factory function:
```python
def create_new_provider_llm(model_id, **kwargs):
    """Create an LLM for the new provider."""
    # Extract model name from model_id
    model_name = model_id.split('/')[-1] if '/' in model_id else model_id
    
    # Create the LLM
    from langchain.llms import NewProviderLLM
    return NewProviderLLM(
        model_name=model_name,
        # Add provider-specific parameters
        **kwargs
    )
```

2. Update the model factory to include the new provider:
```python
def create_language_model(model_id=None, provider=None, **kwargs):
    # Existing code...
    
    if provider == 'new_provider':
        return create_new_provider_llm(model_id, **kwargs)
    # Other providers...
```

3. Implement provider-specific parameter handling:
```python
def extract_provider_params(provider, kwargs):
    """Extract provider-specific parameters."""
    if provider == 'new_provider':
        return {
            'api_key': kwargs.get('api_key') or os.environ.get('NEW_PROVIDER_API_KEY'),
            'api_base': kwargs.get('api_base') or os.environ.get('NEW_PROVIDER_API_BASE'),
            # Other parameters...
        }
    # Other providers...
```

This approach allows you to easily extend the system to support new model providers as they become available.
