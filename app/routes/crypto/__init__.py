"""
Crypto blueprint initialization.
This blueprint handles cryptocurrency data functionality.
"""
from flask import Blueprint

crypto_bp = Blueprint('crypto', __name__)

from app.routes.crypto import routes
