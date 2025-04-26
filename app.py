"""
TechSaaS - Main Application

This is the entry point for the TechSaaS application. It initializes the Flask app
and runs the development server.
"""

import os
from app import create_app

# Create the Flask application instance
app = create_app(os.getenv('FLASK_ENV') or 'development')

if __name__ == '__main__':
    # Run the application with host and port specified
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
