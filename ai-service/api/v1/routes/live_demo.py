#!/usr/bin/env python3
"""
Live Demo Endpoints for TechSaaS API

These endpoints demonstrate the response formatting and error handling capabilities
of the TechSaaS API in a real-world scenario.
"""

import os
import sys
import json
import time
import logging
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Import response formatter
from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.middleware.error_handlers import APIError, ValidationError, AuthenticationError, PermissionError, TierLimitError, ModelError

# Import multimodal processing if available
try:
    from multimodal.processors.processor_factory import ProcessorFactory
    from multimodal.models.unified_manager import UnifiedModelManager
    multimodal_available = True
except ImportError:
    multimodal_available = False

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
live_demo_bp = Blueprint('live_demo', __name__)
CORS(live_demo_bp)  # Enable CORS for all routes in this blueprint

# Initialize processors if available
processor_factory = None
if multimodal_available:
    processor_factory = ProcessorFactory()

@live_demo_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    start_time = datetime.now().timestamp()
    
    # Basic system health data
    health_data = {
        "status": "operational",
        "api_version": "1.0",
        "components": {
            "database": "connected",
            "cache": "operational",
            "models": "available"
        },
        "uptime": 3600 * 24 * 5  # 5 days (simulated)
    }
    
    # Add multimodal status if available
    if multimodal_available:
        health_data["components"]["multimodal"] = "available"
        
        # Get model provider info from UnifiedModelManager
        try:
            model_manager = UnifiedModelManager()
            health_data["model_providers"] = model_manager.active_providers
        except Exception as e:
            health_data["components"]["models"] = f"error: {str(e)}"
    
    return ResponseFormatter.success_response(
        data=health_data,
        message="TechSaaS API is operational",
        metadata={
            "response_time_ms": int((datetime.now().timestamp() - start_time) * 1000)
        },
        start_time=start_time
    )

@live_demo_bp.route('/demo/success', methods=['GET'])
def demo_success():
    """Demonstrate a successful response"""
    start_time = datetime.now().timestamp()
    
    # Sample data that would be returned from an API call
    data = {
        "user": {
            "id": 12345,
            "username": "demo_user",
            "email": "user@techsaas.tech",
            "plan": "premium",
            "credits_remaining": 750
        },
        "usage_stats": {
            "api_calls_this_month": 1250,
            "data_processed_mb": 512,
            "models_used": ["llama3:8b", "phi3:mini"] 
        },
        "features_enabled": [
            "multimodal_processing",
            "api_access",
            "data_export",
            "advanced_analytics"
        ]
    }
    
    # Metadata about the request
    metadata = {
        "token_count": 150,
        "model": "llama3:8b",
        "request_id": f"req_{int(time.time())}"
    }
    
    # Return formatted success response
    return ResponseFormatter.success_response(
        data=data,
        message="Request processed successfully",
        metadata=metadata,
        status_code=200,
        start_time=start_time
    )

@live_demo_bp.route('/demo/error/<error_type>', methods=['GET'])
def demo_error(error_type):
    """Demonstrate different error responses"""
    start_time = datetime.now().timestamp()
    
    if error_type == "validation":
        # Simulate validation errors
        validation_errors = {
            "username": "Username must be between 3 and 20 characters",
            "email": "Please provide a valid email address",
            "password": "Password must be at least 8 characters and include a number"
        }
        
        return ResponseFormatter.validation_error(
            errors=validation_errors,
            message="Validation failed for user registration",
            status_code=422,
            start_time=start_time
        )
        
    elif error_type == "authentication":
        # Simulate authentication error
        return ResponseFormatter.authentication_error(
            message="Invalid API key or authentication token",
            status_code=401,
            start_time=start_time
        )
        
    elif error_type == "permission":
        # Simulate permission error
        return ResponseFormatter.permission_error(
            message="You do not have permission to access this resource",
            required_role="admin",
            status_code=403,
            start_time=start_time
        )
        
    elif error_type == "tier_limit":
        # Simulate tier limit error
        return ResponseFormatter.tier_limit_error(
            tier="basic",
            limit_type="api_calls_per_day",
            current_usage=105,
            allowed_limit=100,
            message="Daily API call limit exceeded",
            status_code=429,
            start_time=start_time
        )
        
    elif error_type == "model":
        # Simulate model error
        return ResponseFormatter.model_error(
            error="Model could not process input due to token limit exceeded",
            model_name="llama3:8b",
            message="AI model encountered an error processing your request",
            status_code=500,
            start_time=start_time
        )
        
    else:
        # Simulate generic API error
        return ResponseFormatter.error_response(
            message=f"Unknown error type: {error_type}",
            status_code=400,
            start_time=start_time
        )

@live_demo_bp.route('/demo/simulate-processing', methods=['POST'])
def simulate_processing():
    """Simulate a processing request with a realistic response time and formatted output"""
    start_time = datetime.now().timestamp()
    
    try:
        # Parse request data
        request_data = request.get_json()
        if not request_data:
            raise ValidationError("Request body must contain valid JSON data")
        
        # Check for required fields
        if "text" not in request_data:
            raise ValidationError({"text": "Text field is required"})
        
        # Validate content length
        text = request_data.get("text", "")
        if len(text) < 10:
            raise ValidationError({"text": "Text must be at least 10 characters"})
        if len(text) > 2000:
            raise ValidationError({"text": "Text cannot exceed 2000 characters"})
        
        # Simulate processing time (0.5-2 seconds)
        processing_time = random.uniform(0.5, 2.0)
        time.sleep(processing_time)
        
        # Simulate token count based on text length (rough estimate)
        token_count = len(text.split()) + int(len(text) / 4)
        
        # Generate simulated processing result
        result = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "estimated_token_count": token_count,
            "sentiment": random.choice(["positive", "neutral", "negative"]),
            "languages_detected": ["en"],
            "processing_id": f"process_{int(time.time())}"
        }
        
        # Add processed text summary (simulated)
        original_words = text.split()
        if len(original_words) > 5:
            # Create a simple "summary" by taking a few words
            summary_length = min(5, max(2, len(original_words) // 3))
            summary_words = random.sample(original_words, summary_length)
            result["summary"] = " ".join(summary_words) + "..."
        else:
            result["summary"] = text
            
        # Add multimodal processing capability if available
        if multimodal_available and processor_factory:
            result["multimodal_capabilities"] = ["text", "image", "video", "audio"]
        
        # Return formatted success response with realistic metadata
        return ResponseFormatter.success_response(
            data=result,
            message="Content processed successfully",
            metadata={
                "token_count": token_count,
                "model": "llama3:8b",
                "processing_time_sec": processing_time,
                "request_id": f"req_{int(time.time())}"
            },
            status_code=200,
            start_time=start_time
        )
    
    except ValidationError as e:
        return ResponseFormatter.validation_error(
            errors=e.errors if hasattr(e, 'errors') else {"error": str(e)},
            message=str(e),
            status_code=422,
            start_time=start_time
        )
    except APIError as e:
        return ResponseFormatter.error_response(
            message=str(e),
            status_code=e.status_code,
            start_time=start_time
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return ResponseFormatter.error_response(
            message="An unexpected error occurred",
            status_code=500,
            start_time=start_time
        )

# Register the blueprint in app.py
def register_blueprint(app):
    """Register the live demo blueprint with the app"""
    app.register_blueprint(live_demo_bp)
