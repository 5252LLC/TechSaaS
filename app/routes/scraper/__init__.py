"""
Scraper blueprint initialization.
This blueprint handles web scraping functionality.
"""
from flask import Blueprint

scraper_bp = Blueprint('scraper', __name__)

from app.routes.scraper import routes
