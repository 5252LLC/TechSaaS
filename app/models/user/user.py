"""
User Model

This module defines the User model for authentication and authorization.
"""

from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app
from app import db

class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.
    
    TEACHING POINT:
    This model demonstrates best practices for handling user authentication:
    1. Password hashing (never store plain text passwords)
    2. Role-based permissions
    3. Account verification
    4. Secure token generation for password resets
    5. Tracking of user activity
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    
    # User information
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    profile_image = db.Column(db.String(128))
    
    # Role and permissions
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'moderator'
    api_key = db.Column(db.String(64), unique=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        """Initialize a new user and generate API key"""
        # Handle is_active conversion to active
        if 'is_active' in kwargs:
            kwargs['active'] = kwargs.pop('is_active')
            
        super(User, self).__init__(**kwargs)
        if self.api_key is None:
            self.api_key = self.generate_api_key()
    
    @property
    def password(self):
        """Prevent password from being accessed"""
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Set password to a hashed value"""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_api_key(self):
        """Generate a unique API key for the user"""
        return str(uuid.uuid4())
    
    def refresh_api_key(self):
        """Generate a new API key for the user"""
        self.api_key = self.generate_api_key()
        return self.api_key
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_admin(self):
        """Check if the user has admin role"""
        return self.role == 'admin'
    
    @property
    def is_moderator(self):
        """Check if the user has moderator role"""
        return self.role == 'moderator' or self.is_admin
    
    @property
    def is_active(self):
        """Check if the user account is active"""
        return self.active
        
    # Flask-Login required methods
    def get_id(self):
        """Return unique identifier for Flask-Login"""
        return str(self.id)
        
    @property
    def is_authenticated(self):
        """Return True if the user is authenticated"""
        return True
        
    @property
    def is_anonymous(self):
        """Return False as we don't support anonymous users"""
        return False
    
    @property
    def full_name(self):
        """Return the user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'
