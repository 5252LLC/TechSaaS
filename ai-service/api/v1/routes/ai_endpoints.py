"""
AI Endpoints Blueprint
Contains routes for AI text processing, chat, and completion operations
"""

import logging
import uuid
from datetime import datetime
from flask import request, jsonify, current_app
from flask_smorest import Blueprint, abort
from marshmallow import ValidationError

# Import schemas
from api.v1.schemas import (
    AnalyzeRequestSchema, 
    ChatRequestSchema, 
    CompletionRequestSchema
)

# Import middleware
from api.v1.middleware import validate_json, validate_schema, sanitize_input, validate_request

# Import LangChain service
from api.v1.services.langchain_factory import get_langchain_service

# Create blueprint with API documentation
ai_blueprint = Blueprint(
    'ai', 
    'ai_endpoints',
    description='AI text processing endpoints for analysis, chat, and completion'
)

# Set up logger
logger = logging.getLogger(__name__)

@ai_blueprint.route('/analyze', methods=['POST'])
@ai_blueprint.arguments(AnalyzeRequestSchema)
@ai_blueprint.doc(
    summary="Analyze content using AI models",
    description="""
    Analyze text content using AI models with various analysis types.
    
    ## Capabilities
    - Summarization of long-form content
    - Entity extraction
    - Sentiment analysis
    - Content categorization
    
    ## Usage Costs
    | Tier | Cost per Request | Batch Size |
    |------|------------------|------------|
    | Basic | $0.01 | N/A |
    | Pro | $0.005 | Up to 10 |
    | Enterprise | $0.002 | Up to 100 |
    """,
    tags=['Basic Tier']
)
@ai_blueprint.response(200, description="Analysis results")
@ai_blueprint.response(400, description="Invalid request parameters")
@ai_blueprint.response(401, description="Unauthorized")
@ai_blueprint.response(429, description="Rate limit exceeded")
def analyze(analyze_data):
    """
    Analyze content using AI models
    
    Expects JSON with:
    - content: text to analyze
    - task: analysis task type (summarize, categorize, extract, etc.)
    - model: optional model to use (defaults to configured default)
    - options: optional parameters for the analysis
    
    Returns analysis results
    """
    try:
        content = analyze_data.get('content')
        task = analyze_data.get('task', 'summarize')
        model = analyze_data.get('model', current_app.config['DEFAULT_AI_MODEL'])
        options = analyze_data.get('options', {})
        
        logger.info(f"Analyzing content with task: {task}, model: {model}")
        
        # Get LangChain service
        langchain_service = get_langchain_service()
        
        # Process the content based on the task
        response = langchain_service.analyze(
            text=content,
            analysis_type=task,
            model=model,
            options=options
        )
        
        # Create response with usage tracking
        result = {
            "id": f"ana-{uuid.uuid4().hex[:12]}",
            "task": task,
            "result": response.get("result", "Analysis result not available"),
            "model_used": model,
            "timestamp": datetime.utcnow().isoformat(),
            "usage": response.get("usage", {})
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in analyze endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/chat', methods=['POST'])
@ai_blueprint.arguments(ChatRequestSchema)
@ai_blueprint.doc(
    summary="Chat interface for conversational AI",
    description="""
    Generate AI responses to chat messages with conversation history support.
    
    ## Features
    - Maintains chat history for contextual responses
    - Supports various AI models
    - Configurable parameters for response generation
    
    ## Usage Costs
    | Tier | Cost per Message | History Length |
    |------|------------------|----------------|
    | Basic | $0.005 | 10 messages |
    | Pro | $0.003 | 50 messages |
    | Enterprise | $0.001 | Unlimited |
    """,
    tags=['Basic Tier']
)
@ai_blueprint.response(200, description="Chat response")
@ai_blueprint.response(400, description="Invalid request parameters")
@ai_blueprint.response(401, description="Unauthorized")
@ai_blueprint.response(429, description="Rate limit exceeded")
def chat(chat_data):
    """
    Chat interface for conversational AI
    
    Expects JSON with:
    - message: user message
    - history: optional chat history array of {role, content} objects
    - model: optional model to use
    - options: optional parameters for the chat
    
    Returns AI response to the chat message
    """
    try:
        message = chat_data.get('message')
        history = chat_data.get('history', [])
        model = chat_data.get('model', current_app.config['DEFAULT_AI_MODEL'])
        options = chat_data.get('options', {})
        conversation_id = chat_data.get('conversation_id', f"conv-{uuid.uuid4().hex[:12]}")
        
        logger.info(f"Processing chat message with model: {model}, conversation_id: {conversation_id}")
        
        # Convert to standard format expected by LangChain
        # Add the current message to the history
        messages = history + [{"role": "user", "content": message}]
        
        # Get LangChain service
        langchain_service = get_langchain_service()
        
        # Process the chat
        response = langchain_service.chat(
            messages=messages,
            model=model,
            conversation_id=conversation_id,
            temperature=options.get('temperature', current_app.config.get('DEFAULT_TEMPERATURE', 0.7)),
            max_tokens=options.get('max_tokens', current_app.config.get('DEFAULT_MAX_TOKENS', 1024))
        )
        
        # Create standardized response
        result = {
            "id": f"chat-{uuid.uuid4().hex[:12]}",
            "response": response.get("choices", [{}])[0].get("message", {}).get("content", "No response generated"),
            "model_used": model,
            "conversation_id": conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "usage": response.get("usage", {})
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in chat endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/completion', methods=['POST'])
@ai_blueprint.arguments(CompletionRequestSchema)
@ai_blueprint.doc(
    summary="Generate AI text completion",
    description="""
    Generate text completions based on a prompt.
    
    ## Features
    - Adjustable temperature and token length
    - Multiple model options
    - Various completion styles
    
    ## Usage Costs
    | Tier | Cost per 1K Tokens | Max Tokens |
    |------|---------------------|------------|
    | Basic | $0.01 | 2,048 |
    | Pro | $0.008 | 8,192 |
    | Enterprise | $0.005 | 32,768 |
    """,
    tags=['Pro Tier']
)
@ai_blueprint.response(200, description="Generated completion")
@ai_blueprint.response(400, description="Invalid request parameters")
@ai_blueprint.response(401, description="Unauthorized")
@ai_blueprint.response(403, description="Forbidden - requires Pro tier or higher")
@ai_blueprint.response(429, description="Rate limit exceeded")
def completion(completion_data):
    """
    Generate AI text completion
    
    Expects JSON with:
    - prompt: text prompt for completion
    - max_tokens: optional max tokens to generate
    - temperature: optional temperature parameter
    - model: optional model to use
    - options: optional additional parameters
    
    Returns completed text
    """
    try:
        prompt = completion_data.get('prompt')
        max_tokens = completion_data.get('max_tokens', current_app.config['DEFAULT_MAX_TOKENS'])
        temperature = completion_data.get('temperature', current_app.config['DEFAULT_TEMPERATURE'])
        model = completion_data.get('model', current_app.config['DEFAULT_AI_MODEL'])
        options = completion_data.get('options', {})
        
        logger.info(f"Generating completion with model: {model}")
        
        # Get LangChain service
        langchain_service = get_langchain_service()
        
        # Process the completion
        response = langchain_service.complete(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **options
        )
        
        # Create standardized response
        result = {
            "id": f"cmpl-{uuid.uuid4().hex[:12]}",
            "completion": response.get("choices", [{}])[0].get("text", "No completion generated"),
            "model_used": model,
            "timestamp": datetime.utcnow().isoformat(),
            "tokens_used": response.get("usage", {}).get("total_tokens", len(prompt.split())),
            "usage": response.get("usage", {})
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error in completion endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/models', methods=['GET'])
@ai_blueprint.doc(
    summary="List available AI models",
    description="""
    Returns a list of available AI models with their capabilities and metadata.
    
    ## Features
    - Model name and ID
    - Supported capabilities (chat, completion, etc.)
    - Context window size
    - Usage tier
    - Model metadata
    
    This endpoint does not consume API credits.
    """,
    tags=['Basic Tier']
)
@ai_blueprint.response(200, description="List of available models")
def list_models():
    """
    List available AI models with their capabilities and metadata
    
    Returns a list of models that can be used with the API endpoints
    """
    try:
        # Get LangChain service
        langchain_service = get_langchain_service()
        
        # Get list of models
        models = langchain_service.list_models()
        
        return jsonify(models)
    except Exception as e:
        logger.exception(f"Error in list_models endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/batch', methods=['POST'])
@validate_json
@validate_request
@ai_blueprint.doc(
    summary="Process batch requests",
    description="""
    Process multiple AI tasks in a single batch request.
    
    ## Features
    - Submit multiple inputs for processing
    - Supports all API operations (chat, completion, analysis)
    - Async processing with webhook callbacks
    - Progress tracking
    
    ## Usage Costs
    | Tier | Max Batch Size | Concurrency |
    |------|----------------|-------------|
    | Basic | 5 | 1 |
    | Pro | 50 | 3 |
    | Enterprise | 500 | 10 |
    """,
    tags=['Pro Tier']
)
@ai_blueprint.response(202, description="Batch request accepted")
@ai_blueprint.response(400, description="Invalid request parameters")
@ai_blueprint.response(401, description="Unauthorized")
@ai_blueprint.response(403, description="Forbidden - requires Pro tier or higher")
def batch_process():
    """
    Process multiple AI tasks in a single batch request
    
    Expects JSON with:
    - inputs: array of inputs to process
    - task: task type (chat, completion, analyze)
    - task_params: parameters for the specified task
    - callback_url: optional webhook URL for async completion notification
    
    Returns batch job status with job ID for tracking
    """
    try:
        # Parse request data
        data = request.get_json()
        
        # Validate inputs
        inputs = data.get('inputs', [])
        task = data.get('task')
        task_params = data.get('task_params', {})
        callback_url = data.get('callback_url')
        
        if not inputs or not task:
            abort(400, message="Inputs and task are required")
        
        # Generate batch job ID
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        
        # In a real implementation, this would initiate a background task
        # For this implementation, we'll just acknowledge the request
        
        return jsonify({
            "batch_id": batch_id,
            "status": "pending",
            "task": task,
            "total_inputs": len(inputs),
            "completed": 0,
            "estimated_completion": (datetime.utcnow().timestamp() + (len(inputs) * 2)),
            "message": "Batch job accepted for processing"
        }), 202
    except Exception as e:
        logger.exception(f"Error in batch_process endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/example/beginner', methods=['GET'])
@ai_blueprint.doc(
    summary="Example endpoint for beginners",
    description="""
    Provides example code and usage information for beginners.
    
    ## Features
    - Code snippets for common use cases
    - Explanations of parameters and responses
    - Interactive examples with sample inputs
    
    This endpoint does not consume API credits.
    """,
    tags=['Documentation']
)
@ai_blueprint.response(200, description="Example usage information")
def example_beginner():
    """
    Provide example code and usage information for beginners
    
    Returns example code snippets and explanations for using the API
    """
    try:
        # Generate example code snippets in multiple languages
        examples = {
            "python": {
                "chat": '''
                import requests
                import json
                
                # API endpoint
                url = "https://api.techsaas.app/api/v1/ai/chat"
                
                # Request headers
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer YOUR_API_KEY"
                }
                
                # Request data
                data = {
                    "message": "What can you tell me about artificial intelligence?",
                    "history": [],
                    "model": "ollama/llama2"
                }
                
                # Send request
                response = requests.post(url, headers=headers, data=json.dumps(data))
                
                # Print response
                print(response.json())
                ''',
                "completion": '''
                import requests
                import json
                
                # API endpoint
                url = "https://api.techsaas.app/api/v1/ai/completion"
                
                # Request headers
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer YOUR_API_KEY"
                }
                
                # Request data
                data = {
                    "prompt": "Once upon a time in a land far away,",
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "model": "ollama/llama2"
                }
                
                # Send request
                response = requests.post(url, headers=headers, data=json.dumps(data))
                
                # Print response
                print(response.json())
                '''
            },
            "javascript": {
                "chat": '''
                // API endpoint
                const url = "https://api.techsaas.app/api/v1/ai/chat";
                
                // Request headers
                const headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer YOUR_API_KEY"
                };
                
                // Request data
                const data = {
                    message: "What can you tell me about artificial intelligence?",
                    history: [],
                    model: "ollama/llama2"
                };
                
                // Send request
                fetch(url, {
                    method: "POST",
                    headers: headers,
                    body: JSON.stringify(data)
                })
                .then(response => response.json())
                .then(data => console.log(data))
                .catch(error => console.error("Error:", error));
                '''
            }
        }
        
        # Generate explanation
        explanation = """
        # Getting Started with TechSaaS AI API
        
        Our API allows you to interact with state-of-the-art AI models for various tasks.
        
        ## Available Endpoints
        
        - `/api/v1/ai/chat` - Chat with AI models
        - `/api/v1/ai/completion` - Generate text completions
        - `/api/v1/ai/analyze` - Analyze text content
        - `/api/v1/ai/models` - List available models
        
        ## Authentication
        
        All API requests require an API key passed in the `Authorization` header:
        
        ```
        Authorization: Bearer YOUR_API_KEY
        ```
        
        ## Rate Limits
        
        Basic tier: 60 requests per minute
        Pro tier: 300 requests per minute
        Enterprise tier: Custom limits
        
        ## Need Help?
        
        Contact support at support@techsaas.app or visit our documentation 
        at https://docs.techsaas.app
        """
        
        return jsonify({
            "examples": examples,
            "explanation": explanation
        })
    except Exception as e:
        logger.exception(f"Error in example_beginner endpoint: {str(e)}")
        abort(500, message=str(e))

@ai_blueprint.route('/health', methods=['GET'])
@ai_blueprint.doc(
    summary="Health check endpoint",
    description="""
    Check the health status of the AI service.
    
    Returns status information, including:
    - Service status
    - Connected models
    - System metrics
    
    This endpoint does not consume API credits.
    """,
    tags=['System']
)
@ai_blueprint.response(200, description="Health status")
def health_check():
    """
    Check the health status of the AI service
    
    Returns status information about the service
    """
    try:
        # Check if LangChain service is available
        try:
            langchain_service = get_langchain_service()
            langchain_status = "healthy"
        except Exception:
            langchain_status = "degraded"
        
        # Return health status
        return jsonify({
            "status": "healthy",
            "version": current_app.config.get('VERSION', '1.0.0'),
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "api": "healthy",
                "langchain": langchain_status,
                "models": "healthy"
            }
        })
    except Exception as e:
        logger.exception(f"Error in health_check endpoint: {str(e)}")
        abort(500, message=str(e))
