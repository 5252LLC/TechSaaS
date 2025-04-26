"""
Scraped Video Model

This module defines the ScrapedVideo model for storing and managing extracted video content.
"""

from datetime import datetime
import json
import re
from urllib.parse import urlparse, parse_qs
from app import db

class ScrapedVideo(db.Model):
    """
    ScrapedVideo model for storing extracted video information.
    
    TEACHING POINT:
    This model demonstrates:
    1. Specialized data modeling for video content
    2. URL parsing and normalization for different video platforms
    3. Metadata extraction from video sources
    4. Platform-specific handling (YouTube, Vimeo, etc.)
    """
    __tablename__ = 'scraped_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    source_url = db.Column(db.String(512), nullable=False, index=True)  # Page URL where video was found
    video_url = db.Column(db.String(512), nullable=False)  # Direct URL to the video
    embed_url = db.Column(db.String(512))  # Embeddable URL (e.g., YouTube embed)
    
    # Video metadata
    title = db.Column(db.String(256))
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # Duration in seconds
    thumbnail_url = db.Column(db.String(512))
    platform = db.Column(db.String(64))  # 'youtube', 'vimeo', 'dailymotion', etc.
    video_id = db.Column(db.String(64))  # Platform-specific ID
    
    # Additional metadata stored as JSON
    video_metadata = db.Column(db.Text)  # Additional platform-specific metadata
    
    # Timestamps and user association
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Batch identifier for grouping videos from the same scrape operation
    scrape_batch_id = db.Column(db.String(64), index=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('scraped_videos', lazy='dynamic'))
    
    def __init__(self, **kwargs):
        """Initialize a new ScrapedVideo instance with automatic platform detection"""
        super(ScrapedVideo, self).__init__(**kwargs)
        
        # Auto-detect platform and ID if not provided
        if self.video_url and not self.platform:
            self.detect_platform_and_id()
        
        # Generate embed URL if not provided
        if self.video_url and self.platform and self.video_id and not self.embed_url:
            self.generate_embed_url()
    
    def detect_platform_and_id(self):
        """
        Detect video platform and extract ID from video URL.
        Supports YouTube, Vimeo, Dailymotion, and more.
        """
        url = self.video_url.lower()
        parsed_url = urlparse(url)
        
        # YouTube detection
        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            self.platform = 'youtube'
            
            # Handle youtu.be short URLs
            if 'youtu.be' in parsed_url.netloc:
                self.video_id = parsed_url.path.strip('/')
            
            # Handle youtube.com/watch?v= URLs
            elif 'watch' in parsed_url.path:
                query = parse_qs(parsed_url.query)
                self.video_id = query.get('v', [''])[0]
            
            # Handle youtube.com/embed/ URLs
            elif 'embed' in parsed_url.path:
                path_parts = parsed_url.path.split('/')
                self.video_id = path_parts[-1]
        
        # Vimeo detection
        elif 'vimeo.com' in parsed_url.netloc:
            self.platform = 'vimeo'
            # Extract ID from path (typically vimeo.com/123456789)
            match = re.search(r'vimeo\.com/(\d+)', url)
            if match:
                self.video_id = match.group(1)
            else:
                # Try player URL format
                match = re.search(r'player\.vimeo\.com/video/(\d+)', url)
                if match:
                    self.video_id = match.group(1)
        
        # Dailymotion detection
        elif 'dailymotion.com' in parsed_url.netloc:
            self.platform = 'dailymotion'
            # Extract ID from path (dailymotion.com/video/x7tgad)
            match = re.search(r'dailymotion\.com/video/([a-zA-Z0-9]+)', url)
            if match:
                self.video_id = match.group(1)
        
        # Facebook detection
        elif 'facebook.com' in parsed_url.netloc:
            self.platform = 'facebook'
            
            # Extract video ID from Facebook URLs
            if 'watch' in parsed_url.path:
                query = parse_qs(parsed_url.query)
                self.video_id = query.get('v', [''])[0]
            elif 'videos' in parsed_url.path:
                path_parts = parsed_url.path.split('/')
                for part in path_parts:
                    if part.isdigit():
                        self.video_id = part
                        break
        
        # Generic video detection (less accurate)
        elif any(ext in url for ext in ['.mp4', '.webm', '.ogg']):
            self.platform = 'direct'
            self.video_id = url.split('/')[-1]
    
    def generate_embed_url(self):
        """Generate appropriate embed URL based on platform and video ID"""
        if not self.platform or not self.video_id:
            return
        
        if self.platform == 'youtube':
            self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"
        
        elif self.platform == 'vimeo':
            self.embed_url = f"https://player.vimeo.com/video/{self.video_id}"
        
        elif self.platform == 'dailymotion':
            self.embed_url = f"https://www.dailymotion.com/embed/video/{self.video_id}"
        
        elif self.platform == 'facebook':
            self.embed_url = f"https://www.facebook.com/plugins/video.php?href=https://www.facebook.com/watch/?v={self.video_id}"
        
        elif self.platform == 'direct':
            # For direct videos, the embed URL is the same as the video URL
            self.embed_url = self.video_url
    
    @property
    def metadata_dict(self):
        """Get metadata as a dictionary"""
        if not self.video_metadata:
            return {}
        return json.loads(self.video_metadata)
    
    def set_metadata(self, metadata_dict):
        """Set metadata from a dictionary"""
        self.video_metadata = json.dumps(metadata_dict)
    
    def to_dict(self):
        """Convert model to dictionary for API responses and exports"""
        return {
            'id': self.id,
            'source_url': self.source_url,
            'video_url': self.video_url,
            'embed_url': self.embed_url,
            'title': self.title,
            'description': self.description,
            'duration': self.duration,
            'thumbnail_url': self.thumbnail_url,
            'platform': self.platform,
            'video_id': self.video_id,
            'scrape_batch_id': self.scrape_batch_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def to_full_dict(self):
        """Convert model to complete dictionary including metadata"""
        full_dict = self.to_dict()
        
        # Add metadata if available
        if self.video_metadata:
            full_dict['metadata'] = self.metadata_dict
        
        return full_dict
    
    def __repr__(self):
        return f'<ScrapedVideo {self.platform}:{self.video_id}>'
