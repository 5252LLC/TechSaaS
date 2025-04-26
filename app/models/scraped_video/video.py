"""
Video Model

This module imports the ScrapedVideo model to maintain backward compatibility
with the import in models/__init__.py
"""

from app.models.scraped_video.scraped_video import ScrapedVideo

# Re-export the ScrapedVideo class for backward compatibility
__all__ = ['ScrapedVideo']
