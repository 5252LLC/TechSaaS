"""
Example routes to demonstrate request validation middleware
"""

import logging
from flask import Blueprint, jsonify, request, g
from flask_smorest import Blueprint, abort

from api.v1.middleware import (
    validate_request,
    require_auth,
    require_tier
)

from api.v1.schemas.validation_example import (
    TextAnalysisSchema,
    ImageAnalysisSchema,
    CompletionRequestSchema
)

# Create blueprint
validation_example_blueprint = Blueprint(
    'validation_example',
    'validation_example',
    description='Examples demonstrating request validation middleware'
)

# Set up logger
logger = logging.getLogger(__name__)

@validation_example_blueprint.route('/text/analyze', methods=['POST'])
@require_auth
@require_tier('basic')  # Accessible to all tiers
@validate_request(TextAnalysisSchema)
def analyze_text():
    """
    Analyze text content
    
    This example endpoint demonstrates using the request validation middleware
    with a marshmallow schema to validate and sanitize input.
    
    The TextAnalysisSchema ensures:
    - 'text' field is required and length-limited
    - 'model' field is optional with a default value
    - 'options' field is an optional dictionary
    """
    # Access the validated data from Flask's g object
    validated_data = g.validated_data
    
    # In a real implementation, we would process the text here
    # For demonstration, we just echo back the request
    response = {
        "request": validated_data,
        "result": {
            "sentiment": "positive",
            "entities": ["example"],
            "summary": "This is a demonstration of request validation."
        },
        "model_used": validated_data.get("model", "ollama/llama2"),
        "processing_time_ms": 120
    }
    
    return jsonify(response)

@validation_example_blueprint.route('/image/analyze', methods=['POST'])
@require_auth
@require_tier('pro')  # Requires Pro tier or higher
@validate_request(ImageAnalysisSchema)
def analyze_image():
    """
    Analyze an image from a URL
    
    This example endpoint demonstrates using both authentication and
    validation middleware together.
    
    The ImageAnalysisSchema ensures:
    - 'image_url' field is required and must be a valid URL
    - 'analysis_type' must be one of the allowed values
    - 'include_metadata' is an optional boolean
    """
    # Access the validated data
    validated_data = g.validated_data
    image_url = validated_data["image_url"]
    analysis_type = validated_data["analysis_type"]
    
    # In a real implementation, we would process the image here
    # For demonstration, we just echo back the request parameters
    response = {
        "request": validated_data,
        "result": {
            "analysis_type": analysis_type,
            "features_detected": ["example_feature"],
            "confidence": 0.95
        },
        "metadata": {
            "image_dimensions": "800x600",
            "format": "jpeg"
        } if validated_data.get("include_metadata", False) else None,
        "processing_time_ms": 350
    }
    
    return jsonify(response)

@validation_example_blueprint.route('/text/completion', methods=['POST'])
@require_auth
@require_tier('pro')  # Requires Pro tier or higher
@validate_request(CompletionRequestSchema)
def text_completion():
    """
    Generate text completion based on a prompt
    
    This example endpoint demonstrates validation of numerical parameters
    with range constraints.
    
    The CompletionRequestSchema ensures:
    - 'prompt' field is required and length-limited
    - 'max_tokens' is validated to be within a reasonable range
    - 'temperature' is validated to be between 0.0 and 1.0
    """
    # Access the validated data
    validated_data = g.validated_data
    
    # In a real implementation, we would call an AI model here
    # For demonstration, we just echo back a sample completion
    response = {
        "request": {
            "prompt": validated_data["prompt"],
            "max_tokens": validated_data.get("max_tokens", 256),
            "temperature": validated_data.get("temperature", 0.7),
            "model": validated_data.get("model", "ollama/llama2")
        },
        "completion": "This is a sample text completion generated based on the provided prompt.",
        "usage": {
            "prompt_tokens": len(validated_data["prompt"].split()),
            "completion_tokens": 12,
            "total_tokens": len(validated_data["prompt"].split()) + 12
        },
        "processing_time_ms": 250
    }
    
    return jsonify(response)
