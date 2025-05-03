#!/usr/bin/env python3
"""
TechSaaS Platform - AI Service Entry Point
WSGI entry point for the Flask application
"""

import os
import sys

# Ensure the directory containing this file is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import application factory
from api.app import create_app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('AI_SERVICE_PORT', 5550))
    
    print(f"Starting {app.config['APP_NAME']} v{app.config['VERSION']} on port {port}")
    print(f"Environment: {app.config['ENV']}")
    print(f"Debug mode: {app.config['DEBUG']}")
    
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
