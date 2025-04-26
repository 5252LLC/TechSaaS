"""
Authentication blueprint initialization.
This blueprint handles user authentication functionality.
"""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from app.routes.auth import routes
