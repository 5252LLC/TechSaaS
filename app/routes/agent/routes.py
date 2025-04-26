"""
Routes for AI agent functionality.
"""
from flask import render_template, request, jsonify, current_app
from app.routes.agent import agent_bp

@agent_bp.route('/', methods=['GET'])
def index():
    """AI agent dashboard landing page."""
    return render_template('agent/index.html')

@agent_bp.route('/chat', methods=['POST'])
def chat():
    """Process chat messages with AI agent."""
    message = request.json.get('message', '')
    
    # Placeholder for actual AI processing
    response = f"Echo: {message}"
    
    return jsonify({'response': response})
