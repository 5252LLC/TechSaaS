"""
Video blueprint initialization.
This blueprint handles video extraction functionality.
"""
from flask import Blueprint

video_bp = Blueprint('video', __name__)

from app.routes.video import routes
