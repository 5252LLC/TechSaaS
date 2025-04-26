"""
UserProfile Model

This module defines the UserProfile model for storing additional user information.
"""

from datetime import datetime
from app import db

class UserProfile(db.Model):
    """
    UserProfile model for storing additional user information beyond authentication data.
    
    This model has a one-to-one relationship with the User model, allowing us to
    keep the User model focused on authentication while storing additional profile
    information separately.
    """
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    
    # Personal information
    bio = db.Column(db.Text)
    location = db.Column(db.String(64))
    website = db.Column(db.String(128))
    
    # Profile customization
    theme = db.Column(db.String(20), default='dark')  # 'dark', 'light'
    avatar = db.Column(db.String(128))
    
    # Preferences
    email_notifications = db.Column(db.Boolean, default=True)
    api_access = db.Column(db.Boolean, default=False)
    default_proxy_enabled = db.Column(db.Boolean, default=True)
    
    # Usage statistics
    scraper_requests_count = db.Column(db.Integer, default=0)
    video_extractions_count = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserProfile {self.id}>'
    
    def increment_scraper_count(self):
        """Increment the scraper requests count"""
        self.scraper_requests_count += 1
        self.last_active = datetime.utcnow()
        db.session.add(self)
    
    def increment_video_count(self):
        """Increment the video extractions count"""
        self.video_extractions_count += 1
        self.last_active = datetime.utcnow()
        db.session.add(self)
    
    @staticmethod
    def create_profile_for_user(user_id):
        """
        Create a default profile for a new user
        
        Args:
            user_id: The ID of the user to create a profile for
            
        Returns:
            The newly created UserProfile instance
        """
        profile = UserProfile(
            user_id=user_id,
            theme='dark',  # Default to dark theme for TechSaaS branding
            email_notifications=True,
            default_proxy_enabled=True
        )
        db.session.add(profile)
        db.session.commit()
        return profile
