"""
LangChain Example Routes

This module provides example endpoints demonstrating the integration of LangChain
with the Flask API for various AI tasks.
"""

import logging
from flask import Blueprint, jsonify, request, g
from flask_smorest import Blueprint, abort

from api.v1.middleware import (
    validate_request,
    require_auth,
    require_tier,
    track_usage
)

from api.v1.services.langchain_factory import (
    get_langchain_service,
    get_user_memory_manager,
    create_chain_for_task
)

# Create schemas for request validation
from marshmallow import Schema, fields, validate

# Schema definitions for LangChain endpoints
class ConversationSchema(Schema):
    """Schema for conversation requests"""
    message = fields.String(required=True, validate=validate.Length(min=1, max=4096))
    conversation_id = fields.String(required=False)
    system_prompt = fields.String(required=False)
    stream = fields.Boolean(required=False, default=False)

class CompletionSchema(Schema):
    """Schema for text completion requests"""
    prompt = fields.String(required=True, validate=validate.Length(min=1, max=4096))
    max_tokens = fields.Integer(required=False, default=256, validate=validate.Range(min=1, max=4096))
    temperature = fields.Float(required=False, default=0.7, validate=validate.Range(min=0.0, max=1.0))
    model = fields.String(required=False)

class AnalysisSchema(Schema):
    """Schema for text analysis requests"""
    text = fields.String(required=True, validate=validate.Length(min=1, max=8192))
    analysis_type = fields.String(
        required=True,
        validate=validate.OneOf(['sentiment', 'entities', 'summarization', 'keywords'])
    )
    model = fields.String(required=False)

# Create blueprint
langchain_example_blueprint = Blueprint(
    'langchain_example',
    'langchain_example',
    description='Examples demonstrating LangChain integration'
)

# Set up logger
logger = logging.getLogger(__name__)

@langchain_example_blueprint.route('/conversation', methods=['POST'])
@require_auth
@require_tier('basic')  # Available to all tiers
@validate_request(ConversationSchema)
@track_usage
def conversation():
    """
    Chat conversation endpoint using LangChain
    
    This endpoint demonstrates using LangChain for a conversational interface
    with memory persistence across multiple requests.
    """
    try:
        # Get validated data
        data = g.validated_data
        message = data['message']
        conversation_id = data.get('conversation_id', request.headers.get('X-Conversation-ID'))
        system_prompt = data.get('system_prompt')
        stream = data.get('stream', False)
        
        # Get user_id from auth middleware
        user_id = g.user_id if hasattr(g, 'user_id') else 'anonymous'
        
        # Use conversation_id if provided, otherwise use user_id
        memory_id = conversation_id or user_id
        
        # Get memory manager and store in g for after_request hook
        memory_manager = get_user_memory_manager(memory_id)
        g.memory_manager = memory_manager
        g.user_id = memory_id
        
        # Create conversation chain
        service = get_langchain_service()
        
        # Use system prompt if provided
        if system_prompt:
            memory_manager.add_system_message(system_prompt)
        
        # Generate response
        # Use streaming or normal response based on request
        if stream:
            # Streaming is implemented differently based on your front-end needs
            # This is a simple approach that doesn't actually stream to the client
            response_text = service.generate_streaming_response(
                message,
                memory_manager=memory_manager
            )
        else:
            response_text = service.generate_response(
                message,
                memory_manager=memory_manager
            )
            
        # Create response object
        response = {
            "text": response_text,
            "conversation_id": memory_id,
            "usage": {
                "prompt_tokens": len(message.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(message.split()) + len(response_text.split())
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.exception(f"Error in conversation endpoint: {str(e)}")
        abort(500, message=f"Error generating conversation response: {str(e)}")

@langchain_example_blueprint.route('/completion', methods=['POST'])
@require_auth
@require_tier('pro')  # Requires Pro tier or higher
@validate_request(CompletionSchema)
@track_usage
def completion():
    """
    Text completion endpoint using LangChain
    
    This endpoint demonstrates using LangChain for text completion tasks
    without memory persistence.
    """
    try:
        # Get validated data
        data = g.validated_data
        prompt = data['prompt']
        max_tokens = data.get('max_tokens', 256)
        temperature = data.get('temperature', 0.7)
        model = data.get('model')
        
        # Get LangChain service
        service = get_langchain_service()
        
        # Use a specific model if requested
        if model:
            service.switch_model(model)
        
        # Create completion chain
        chain = create_chain_for_task('completion')
        
        # Set model parameters
        service.set_model_parameters({
            'max_tokens': max_tokens,
            'temperature': temperature
        })
        
        # Generate completion
        completion_text = service.generate_completion(prompt)
        
        # Create response object
        response = {
            "completion": completion_text,
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(completion_text.split()),
                "total_tokens": len(prompt.split()) + len(completion_text.split())
            },
            "model": service.get_model_name()
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.exception(f"Error in completion endpoint: {str(e)}")
        abort(500, message=f"Error generating completion: {str(e)}")

@langchain_example_blueprint.route('/analysis', methods=['POST'])
@require_auth
@require_tier('basic')  # Basic tier or higher
@validate_request(AnalysisSchema)
@track_usage
def text_analysis():
    """
    Text analysis endpoint using LangChain
    
    This endpoint demonstrates using LangChain for different text analysis tasks
    such as sentiment analysis, entity extraction, summarization, etc.
    """
    try:
        # Get validated data
        data = g.validated_data
        text = data['text']
        analysis_type = data['analysis_type']
        model = data.get('model')
        
        # Get LangChain service
        service = get_langchain_service()
        
        # Use a specific model if requested
        if model:
            service.switch_model(model)
        
        # Create analysis chain
        chain = create_chain_for_task('analysis')
        
        # Perform the requested analysis
        if analysis_type == 'sentiment':
            result = service.analyze_sentiment(text)
        elif analysis_type == 'entities':
            result = service.extract_entities(text)
        elif analysis_type == 'summarization':
            result = service.summarize_text(text)
        elif analysis_type == 'keywords':
            result = service.extract_keywords(text)
        else:
            abort(400, message=f"Unsupported analysis type: {analysis_type}")
        
        # Create response object
        response = {
            "analysis_type": analysis_type,
            "result": result,
            "usage": {
                "input_tokens": len(text.split()),
                "output_tokens": len(str(result).split()) if isinstance(result, str) else 50,
                "total_tokens": len(text.split()) + (len(str(result).split()) if isinstance(result, str) else 50)
            },
            "model": service.get_model_name()
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.exception(f"Error in text analysis endpoint: {str(e)}")
        abort(500, message=f"Error performing text analysis: {str(e)}")

@langchain_example_blueprint.route('/models', methods=['GET'])
@require_auth
def list_models():
    """List available LangChain models"""
    try:
        # Get LangChain service
        service = get_langchain_service()
        
        # Get available models
        models = service.list_available_models()
        
        return jsonify({
            "models": models,
            "current_model": service.get_model_name()
        })
    
    except Exception as e:
        logger.exception(f"Error listing models: {str(e)}")
        abort(500, message=f"Error listing available models: {str(e)}")

@langchain_example_blueprint.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for LangChain integration"""
    try:
        # Check if LangChain service is initialized
        service = get_langchain_service()
        model_info = service.get_model_info()
        
        return jsonify({
            'status': 'healthy',
            'model': model_info['name'],
            'backend': model_info.get('backend', 'ollama'),
            'cache_enabled': service.is_caching_enabled(),
            'memory_type': 'persistent' if service.is_persistent_memory() else 'simple'
        })
    except Exception as e:
        logger.exception(f"LangChain health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
