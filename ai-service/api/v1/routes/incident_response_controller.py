"""
Incident Response Controller

Registers the incident_response blueprint with the Flask application.
Provides a consistent route registration pattern aligned with other components.

Author: TechSaaS Security Team
Date: May 5, 2025
"""

from flask import Flask
from ..routes.incident_response import incident_blueprint, register_incident_routes

def init_app(app: Flask) -> None:
    """
    Initialize incident response routes with the Flask application.
    
    Args:
        app (Flask): The Flask application instance
    """
    # Register the incident_response blueprint with the app
    register_incident_routes(app)
    
    # Log successful registration
    app.logger.info("Incident Response routes registered successfully")
