"""
Audit Trail Database Models

This module provides the database models for storing audit trail events
in a structured and queryable format.
"""

from datetime import datetime
from sqlalchemy import JSON
from flask_sqlalchemy import SQLAlchemy
from api.v1.models.base import db, BaseModel

class AuditEvent(db.Model, BaseModel):
    """
    Model for storing audit trail events
    
    Provides a tamper-evident record of all important actions in the system
    """
    __tablename__ = 'audit_events'

    # Primary identifier
    event_id = db.Column(db.String(36), primary_key=True)
    
    # When the event occurred
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)
    
    # Event classification
    event_type = db.Column(db.String(50), index=True, nullable=False)
    action = db.Column(db.String(50), index=True, nullable=False)
    
    # Who performed the action
    actor_id = db.Column(db.String(36), index=True, nullable=False)
    actor_type = db.Column(db.String(20), index=True, nullable=False)
    
    # What was affected
    resource_id = db.Column(db.String(255), index=True, nullable=True)
    resource_type = db.Column(db.String(50), index=True, nullable=True)
    
    # Result of the action
    outcome = db.Column(db.String(20), index=True, nullable=False)
    
    # Additional context
    details = db.Column(JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    request_id = db.Column(db.String(36), index=True, nullable=True)
    
    # Integrity verification
    hash = db.Column(db.String(64), nullable=False)
    
    def __init__(self, event_id=None, timestamp=None, event_type=None, action=None, 
                 actor_id=None, actor_type=None, resource_id=None, resource_type=None, 
                 outcome=None, details=None, ip_address=None, user_agent=None, 
                 request_id=None, hash=None, **kwargs):
        """Initialize an AuditEvent database model
        
        This constructor allows creating an AuditEvent from the utility class
        or from individual parameters.
        """
        self.event_id = event_id
        self.timestamp = timestamp
        self.event_type = event_type
        self.action = action
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.outcome = outcome
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id
        self.hash = hash
    
    def __repr__(self):
        return f"<AuditEvent {self.event_id}: {self.event_type}/{self.action}>"
    
    def to_dict(self):
        """Convert the model to a dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'event_type': self.event_type,
            'action': self.action,
            'actor_id': self.actor_id,
            'actor_type': self.actor_type,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'outcome': self.outcome,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_id': self.request_id,
            'hash': self.hash
        }
    
    @classmethod
    def from_audit_event(cls, audit_event):
        """Create a model instance from an AuditEvent object"""
        event_dict = audit_event.to_dict()
        
        # Convert timestamp string to datetime
        if isinstance(event_dict['timestamp'], str):
            timestamp = event_dict['timestamp'].rstrip('Z')
            event_dict['timestamp'] = datetime.fromisoformat(timestamp)
        
        return cls(**event_dict)


class AuditEventArchive(db.Model, BaseModel):
    """
    Model for storing archived audit trail events
    
    Allows preserving audit data beyond the active retention period
    """
    __tablename__ = 'audit_events_archive'

    # Same schema as AuditEvent
    event_id = db.Column(db.String(36), primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, nullable=False)
    event_type = db.Column(db.String(50), index=True, nullable=False)
    action = db.Column(db.String(50), index=True, nullable=False)
    actor_id = db.Column(db.String(36), index=True, nullable=False)
    actor_type = db.Column(db.String(20), index=True, nullable=False)
    resource_id = db.Column(db.String(255), index=True, nullable=True)
    resource_type = db.Column(db.String(50), index=True, nullable=True)
    outcome = db.Column(db.String(20), index=True, nullable=False)
    details = db.Column(JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    request_id = db.Column(db.String(36), index=True, nullable=True)
    hash = db.Column(db.String(64), nullable=False)
    
    # Archive-specific fields
    archived_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    archive_reason = db.Column(db.String(50), nullable=False)
    
    def __repr__(self):
        return f"<AuditEventArchive {self.event_id}: {self.event_type}/{self.action}>"
