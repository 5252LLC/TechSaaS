"""
Main blueprint initialization.
This blueprint handles general routes like home, about, and contact.
"""
from flask import Blueprint

main_bp = Blueprint('main', __name__)

from app.routes.main import routes
