"""
TechSaaS Models Package

This package contains all the database models for the TechSaaS application.
Import all models here to ensure they are registered with SQLAlchemy before
the database is created or migrated.
"""

# Import User models
from app.models.user.user import User
from app.models.user.role import Role
from app.models.user.user_profile import UserProfile

# Import Scraped Data models
from app.models.scraped_data.scraped_data import ScrapedData
from app.models.scraped_data.scraped_content import ScrapedContent

# Import Video models
from app.models.scraped_video.video import ScrapedVideo

# Define all models that should be available through the models package
__all__ = [
    'User',
    'Role',
    'UserProfile',
    'ScrapedData',
    'ScrapedContent',
    'ScrapedVideo'
]