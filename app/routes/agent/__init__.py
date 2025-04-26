"""
Agent blueprint initialization.
This blueprint handles AI agent functionality.
"""
from flask import Blueprint

agent_bp = Blueprint('agent', __name__)

from app.routes.agent import routes
