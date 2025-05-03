# TechSaaS AI Service Architecture - Personal Reference

This document provides a detailed explanation of the AI service architecture for your personal reference. It outlines how all components fit together and explains the rationale behind key design decisions.

## Complete Architecture Diagram

```
                  ┌─────────────────┐
                  │  API Gateway    │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │  AI Service API  │
                  └────────┬────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
┌──────────▼──────────┐        ┌──────────▼──────────┐
│ LangChain Factory   │        │ Usage Tracking      │
│                     │        │                     │
│ - Model loading     │        │ - Request metering  │
│ - Chain building    │        │ - Quota management  │
│ - Memory management │        │ - Billing data      │
└──────────┬──────────┘        └─────────────────────┘
           │
           │
┌──────────▼──────────┐
│ Compatibility Layer │
│                     │
│ - Version detection │
│ - API normalization │
└──────────┬──────────┘
           │
           │
┌──────────▼──────────┐
│ LangChain           │
└──────────┬──────────┘
           │
           │
┌──────────▼──────────┐
│ Model Providers     │
│                     │
│ - Ollama            │
│ - HuggingFace       │
│ - OpenAI (Future)   │
└─────────────────────┘
```

## Component Breakdown and Implementation Notes

### 1. API Gateway

- **Implementation**: Flask-based RESTful API with proper request validation
- **Security**: JWT authentication, rate limiting, and input validation
- **Purpose**: Provides a unified entry point for all AI capabilities

The API Gateway handles all incoming requests, providing a consistent interface regardless of the underlying model provider. The middleware stack includes:

```python
# Middleware registration sequence
app.before_request(validate_api_key)  # Authentication check
app.before_request(check_rate_limits)  # Rate limiting
app.before_request(sanitize_inputs)   # Input sanitization
app.before_request(track_api_usage)   # Usage metrics
```

### 2. AI Service API

- **Implementation**: Flask blueprints organized by capability
- **Endpoints**: 
  - `/api/v1/ai/chat` - Conversational AI
  - `/api/v1/ai/completion` - Text completion
  - `/api/v1/ai/analyze` - Content analysis
  - `/api/v1/ai/multimodal` - Multi-modal processing

The controller layer uses dependency injection to decouple business logic from request handling:

```python
@ai_bp.route('/chat', methods=['POST'])
@require_api_key
def chat_endpoint():
    request_data = request.get_json()
    
    # Extract parameters with defaults
    message = request_data.get('message', '')
    conversation_id = request_data.get('conversation_id', str(uuid.uuid4()))
    model_id = request_data.get('model', current_app.config['DEFAULT_LLM_MODEL'])
    
    # Delegate to service layer
    service = get_langchain_service()
    
    try:
        response, usage = service.chat(
            message=message,
            conversation_id=conversation_id,
            model_id=model_id
        )
        
        return jsonify({
            'response': response,
            'conversation_id': conversation_id,
            'usage': usage,
            'model': model_id
        })
        
    except Exception as e:
        # Error handling with appropriate status codes
        return handle_service_exception(e)
```

### 3. LangChain Factory

- **Implementation**: Factory pattern with provider-specific adapters
- **Purpose**: Abstracts model provider differences
- **Key feature**: Dynamic configuration based on available models

The factory handles the complexity of creating appropriate LangChain components:

```python
def create_langchain_agent(model_id, tools=None, memory=None):
    """Create a LangChain agent with the specified model and tools."""
    # Extract provider from model_id
    provider, model_name = parse_model_id(model_id)
    
    # Get the LLM
    llm = create_language_model(model_id)
    
    # Create appropriate tools
    if not tools:
        tools = get_default_tools()
    
    # Create memory instance if not provided
    if not memory:
        memory = create_memory_store()
    
    # Create agent
    agent = create_agent_with_tools(llm, tools, memory)
    
    return agent
```

### 4. Usage Tracking

- **Implementation**: Middleware + SQLite database (upgradable to PostgreSQL)
- **Purpose**: Monetization and resource management
- **Schema**: Captures all metrics needed for billing and analytics

The usage tracking system was designed with scalability in mind:

```python
class UsageTracker:
    def __init__(self, db_connection):
        self.db = db_connection
        self._ensure_tables_exist()
    
    def track_request(self, user_id, endpoint, tier, **metrics):
        """Record a single API usage event."""
        timestamp = datetime.utcnow()
        
        # Insert record
        self.db.execute(
            """
            INSERT INTO api_usage (
                user_id, endpoint, timestamp, tier,
                tokens_input, tokens_output, processing_time,
                status_code, model_id, request_size, response_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, endpoint, timestamp, tier,
                metrics.get('tokens_input', 0),
                metrics.get('tokens_output', 0),
                metrics.get('processing_time', 0),
                metrics.get('status_code', 200),
                metrics.get('model_id', None),
                metrics.get('request_size', 0),
                metrics.get('response_size', 0)
            )
        )
        self.db.commit()
    
    def get_usage_summary(self, user_id, start_date, end_date):
        """Get usage summary for a specific user and time period."""
        # Implementation for usage reports and billing
```

### 5. Compatibility Layer

- **Implementation**: Feature detection + proxy methods
- **Purpose**: Maintain compatibility across LangChain versions
- **Approach**: Monkey patching only when necessary

The compatibility layer uses runtime detection to adapt appropriately:

```python
def apply_compatibility_patches():
    """Apply necessary patches based on detected versions."""
    major, minor, patch = detect_langchain_version()
    
    # Apply patches for pre-1.0 LangChain
    if major < 1:
        apply_legacy_patches()
    # Apply patches for early 1.x versions
    elif major == 1 and minor < 3:
        apply_early_v1_patches()
```

### 6. Model Providers

- **Implementation**: Adapter pattern for each provider
- **Supported providers**: Ollama (primary), HuggingFace, OpenAI (future)
- **Configuration**: Environment variables + config file

Provider adapters handle the specific requirements of each model service:

```python
class OllamaAdapter:
    """Adapter for Ollama models."""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    
    def get_llm(self, model_name, **kwargs):
        """Get an Ollama LLM instance."""
        from langchain.llms import Ollama
        
        return Ollama(
            model=model_name,
            base_url=self.base_url,
            **self._filter_relevant_params(kwargs)
        )
    
    def _filter_relevant_params(self, params):
        """Extract only params relevant to Ollama."""
        relevant = {}
        for key in ["temperature", "top_p", "top_k"]:
            if key in params:
                relevant[key] = params[key]
        return relevant
```

## Design Decisions Explained

### Why Factory Pattern for LangChain?

The factory pattern provides several key advantages for our use case:

1. **Abstraction**: Developers don't need to know the intricacies of each provider
2. **Configuration centralization**: All provider-specific configuration is handled in one place
3. **Runtime flexibility**: We can add new providers without changing client code
4. **Testing**: Easy to mock for unit tests

### Why a Compatibility Layer?

LangChain is evolving rapidly, and breaking changes are common. Our compatibility layer:

1. **Reduces maintenance burden**: API changes are isolated to one module
2. **Simplifies upgrades**: We can upgrade LangChain without disrupting service
3. **Protects from bugs**: Issues in newer versions can be patched transparently

### Why Middleware for Usage Tracking?

Using middleware for usage tracking provides:

1. **Separation of concerns**: Core business logic remains clean
2. **Consistent tracking**: All endpoints are tracked the same way
3. **Extensibility**: Easy to add new metrics without changing endpoint code

## Future Enhancements

1. **Streaming Responses**: Implementing streaming for real-time interactions
   - Requires EventSource/Server-Sent Events implementation
   - Need to track token usage incrementally

2. **Caching Layer**: Response caching for improved performance
   - Consider Redis for distributed caching
   - Implement cache invalidation strategies

3. **Admin Dashboard**: Web interface for usage monitoring
   - Built with React for the frontend
   - Real-time metrics using websockets

4. **Advanced Security**: Content filtering and prompt injection protection
   - Implement input classification before processing
   - Add circuit breakers for suspicious patterns

## Performance Considerations

Critical performance optimizations we've implemented:

1. **Lazy Loading**: Models are loaded only when needed
2. **Connection Pooling**: Database connections are pooled for efficiency
3. **Resource Monitoring**: Service includes health check endpoints that report resource usage

## Personal Notes on Implementation

The most challenging aspect was balancing flexibility with performance. The factory pattern adds a small overhead, but the benefits in maintainability and flexibility outweigh this cost.

The compatibility layer was essential but required careful testing to ensure it works correctly with all supported LangChain versions. Future updates to LangChain will require ongoing maintenance of this layer.

Usage tracking was designed to be lightweight but comprehensive. The current implementation adds minimal overhead to requests while collecting all necessary data for our monetization strategy.
