"""
TechSaaS Platform - AI Service
LangChain and Ollama integration for AI capabilities
"""
import os
import sys
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import time
import random
from datetime import datetime

# Add the parent directory to sys.path to allow for imports
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__)

# Try to import response formatter
try:
    from api.v1.utils.response_formatter import ResponseFormatter
    FORMATTER_AVAILABLE = True
    print("Successfully imported ResponseFormatter")
except ImportError as e:
    print(f"Error importing ResponseFormatter: {e}")
    FORMATTER_AVAILABLE = False
    
    # Create a simplified version if not available
    class SimpleResponseFormatter:
        @staticmethod
        def success_response(data=None, message="Operation successful", metadata=None, **kwargs):
            if metadata is None:
                metadata = {}
            response = {
                "status": "success",
                "message": message,
                "data": data,
                "metadata": {
                    **metadata,
                    "timestamp": datetime.now().timestamp(),
                    "processing_time_ms": 0
                }
            }
            return jsonify(response)
            
        @staticmethod
        def error_response(message="An error occurred", status_code=400, **kwargs):
            response = {
                "status": "error",
                "message": message,
                "error": {
                    "type": "general_error",
                    "details": message
                },
                "metadata": {
                    "timestamp": datetime.now().timestamp(),
                    "processing_time_ms": 0
                }
            }
            return jsonify(response), status_code
    
    ResponseFormatter = SimpleResponseFormatter

# Import response formatter and live demo blueprint
try:
    from api.v1.routes.live_demo import live_demo_bp
    
    # Register the live demo blueprint
    app.register_blueprint(live_demo_bp, url_prefix='/api/live-demo')
    print("Registered live demo blueprint successfully")
except ImportError as e:
    print(f"Error importing modules: {e}")

# Configuration
PORT = int(os.getenv('AI_SERVICE_PORT', 5550))
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
AI_MODEL = os.getenv('AI_MODEL', 'llama3.2:3b')
AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', 4096))
AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', 0.2))

@app.route('/api/status')
def status():
    """Status endpoint for health checks"""
    return jsonify({
        "service": "TechSaaS AI Service",
        "version": "1.0.0",
        "status": "operational",
        "model": AI_MODEL,
        "ollama_url": OLLAMA_BASE_URL
    })

@app.route('/api/debug/routes')
def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify({
        'total_routes': len(routes),
        'routes': routes
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Analyze content using LangChain and Ollama
    Expects JSON with content and optional parameters
    """
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({"error": "Content is required"}), 400
            
        content = data.get('content')
        task = data.get('task', 'summarize')
        
        # This is a placeholder for actual LangChain + Ollama integration
        # Will be implemented in Task #7
        
        return jsonify({
            "task": task,
            "result": f"AI analysis of content (placeholder): {content[:50]}...",
            "model_used": AI_MODEL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat interface for conversational AI"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({"error": "Message is required"}), 400
            
        message = data.get('message')
        history = data.get('history', [])
        
        # Placeholder for actual chat implementation with LangChain
        response = f"This is a placeholder response to your message: {message}"
        
        return jsonify({
            "response": response,
            "model_used": AI_MODEL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/models')
def models():
    """List available AI models"""
    # This will be populated with actual data from Ollama
    available_models = [
        {"name": "llama3.2:3b", "status": "loaded"},
        {"name": "grok:3b", "status": "available"}
    ]
    return jsonify({"models": available_models})

@app.route('/api/demo/success')
def demo_success():
    """Demonstrate a successful response with TechSaaS formatting"""
    start_time = datetime.now().timestamp()
    
    # Sample data showcasing user info with subscription tier
    data = {
        "user": {
            "id": 12345,
            "username": "demo_user",
            "email": "user@techsaas.tech",  # Using brand domain
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
    
    # Metadata with token usage tracking for monetization
    metadata = {
        "token_count": 150,
        "model": AI_MODEL,
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

@app.route('/api/demo/error/<error_type>')
def demo_error(error_type):
    """Demonstrate different error responses with TechSaaS formatting"""
    start_time = datetime.now().timestamp()
    
    if error_type == "validation":
        # Simulate validation errors
        validation_errors = {
            "username": "Username must be between 3 and 20 characters",
            "email": "Please provide a valid email address",
            "password": "Password must be at least 8 characters and include a number"
        }
        
        if hasattr(ResponseFormatter, "validation_error"):
            return ResponseFormatter.validation_error(
                errors=validation_errors,
                message="Validation failed for user registration",
                status_code=422,
                start_time=start_time
            )
        else:
            # Fallback if specialized method not available
            return ResponseFormatter.error_response(
                message="Validation failed for user registration",
                error_type="validation_error",
                validation_errors=validation_errors,
                status_code=422,
                start_time=start_time
            )
        
    elif error_type == "tier_limit":
        # Simulate tier limit error - important for monetization strategy
        if hasattr(ResponseFormatter, "tier_limit_error"):
            return ResponseFormatter.tier_limit_error(
                tier="basic",
                limit_type="api_calls_per_day",
                current_usage=105,
                allowed_limit=100,
                message="Daily API call limit exceeded",
                status_code=429,
                start_time=start_time
            )
        else:
            # Fallback if specialized method not available
            return ResponseFormatter.error_response(
                message="Daily API call limit exceeded",
                error_type="tier_limit_error",
                tier="basic",
                current_usage=105,
                allowed_limit=100,
                upgrade_url="https://techsaas.tech/pricing",  # Using brand domain
                status_code=429,
                start_time=start_time
            )
        
    else:
        # Generic error response
        return ResponseFormatter.error_response(
            message=f"Unknown error type: {error_type}",
            status_code=400,
            start_time=start_time
        )

@app.route('/api/demo/process', methods=['POST'])
def demo_process():
    """Simulate processing with realistic response time and formatted output"""
    start_time = datetime.now().timestamp()
    
    try:
        # Parse request data
        request_data = request.get_json()
        if not request_data:
            return ResponseFormatter.error_response(
                message="Request body must contain valid JSON data",
                status_code=400,
                start_time=start_time
            )
        
        # Check for required fields
        if "text" not in request_data:
            return ResponseFormatter.error_response(
                message="Text field is required",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Validate content length
        text = request_data.get("text", "")
        if len(text) < 10:
            return ResponseFormatter.error_response(
                message="Text must be at least 10 characters",
                error_type="validation_error",
                status_code=422,
                start_time=start_time
            )
        
        # Simulate processing time (0.5-1 second)
        processing_time = random.uniform(0.5, 1.0)
        time.sleep(processing_time)
        
        # Simulate token count based on text length
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
        
        # Return formatted success response with usage metrics for billing
        return ResponseFormatter.success_response(
            data=result,
            message="Content processed successfully",
            metadata={
                "token_count": token_count,
                "model": AI_MODEL,
                "processing_time_sec": processing_time,
                "request_id": f"req_{int(time.time())}"
            },
            status_code=200,
            start_time=start_time
        )
    
    except Exception as e:
        # Catch-all error handler
        return ResponseFormatter.error_response(
            message=f"An unexpected error occurred: {str(e)}",
            status_code=500,
            start_time=start_time
        )

if __name__ == '__main__':
    print(f"Starting AI Service on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
