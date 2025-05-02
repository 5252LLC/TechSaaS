"""
TechSaaS Platform - AI Service
LangChain and Ollama integration for AI capabilities
"""
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__)

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

if __name__ == '__main__':
    print(f"Starting AI Service on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
