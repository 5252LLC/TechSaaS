"""
Audit Trail Module

This module provides comprehensive auditing capabilities for the TechSaaS platform,
recording user activities and system events for security and compliance purposes.

Features:
- Structured logging of all system and user events
- Tamper-evident audit records
- Configurable retention policies
- Searchable audit history
- Compliance-ready reporting
"""

import datetime
import json
import logging
import os
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Union
from flask import request, g
import time

# Configure logging
logger = logging.getLogger(__name__)

class AuditEvent:
    """Represents a single audit event in the system"""
    
    # Event types
    USER_AUTHENTICATION = "user_authentication"
    USER_AUTHORIZATION = "user_authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CHANGE = "system_change"
    SECURITY_EVENT = "security_event"
    API_USAGE = "api_usage"
    ADMIN_ACTION = "admin_action"
    PAYMENT_TRANSACTION = "payment_transaction"
    
    # Event outcomes
    OUTCOME_SUCCESS = "success"
    OUTCOME_FAILURE = "failure"
    OUTCOME_ERROR = "error"
    OUTCOME_WARNING = "warning"
    
    def __init__(
        self,
        event_type: str,
        action: str,
        actor_id: Optional[str] = None,
        actor_type: str = "user",
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        outcome: str = OUTCOME_SUCCESS,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """
        Initialize a new audit event.
        
        Args:
            event_type: Type of event (authentication, authorization, data access, etc.)
            action: Specific action performed (login, logout, view, update, etc.)
            actor_id: ID of the user or system performing the action
            actor_type: Type of actor (user, system, service)
            resource_id: ID of the resource being accessed/modified
            resource_type: Type of resource (user, data, system component)
            outcome: Outcome of the action (success, failure, error)
            details: Additional details specific to the event
            ip_address: IP address of the client
            user_agent: User agent of the client
            request_id: Unique ID for the request
        """
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        self.event_type = event_type
        self.action = action
        self.actor_id = actor_id or "anonymous"
        self.actor_type = actor_type
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.outcome = outcome
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id or str(uuid.uuid4())
        
        # Extract request context if in a Flask request
        if not ip_address and request:
            self.ip_address = request.remote_addr
        
        if not user_agent and request:
            self.user_agent = request.user_agent.string if hasattr(request, 'user_agent') else None
        
        # Generate hash for tamper evidence
        self._generate_hash()
    
    def _generate_hash(self):
        """Generate a hash of the event data for tamper evidence"""
        event_data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "action": self.action,
            "actor_id": self.actor_id,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "details": self.details
        }
        
        # Convert to stable JSON string (sorted keys)
        json_data = json.dumps(event_data, sort_keys=True)
        
        # Generate SHA-256 hash
        self.hash = hashlib.sha256(json_data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage/serialization"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "outcome": self.outcome,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "hash": self.hash
        }
    
    def __str__(self) -> str:
        """String representation of the audit event"""
        return f"AuditEvent({self.event_type}, {self.action}, {self.outcome})"


class AuditTrail:
    """Manages the collection, storage, and retrieval of audit events"""
    
    def __init__(self, storage_backend=None, config=None):
        """
        Initialize the audit trail.
        
        Args:
            storage_backend: Backend for storing audit events
            config: Configuration options for the audit trail
        """
        self.config = config or {}
        self.storage = storage_backend or DatabaseAuditStorage()
        self.enabled = self.config.get("enabled", True)
        self.retention_days = self.config.get("retention_days", 365)
        
        # Initialize a chain hash for additional tamper evidence
        self.last_chain_hash = None
    
    def log_event(self, event: Union[AuditEvent, Dict[str, Any]]) -> str:
        """
        Log an audit event to the audit trail.
        
        Args:
            event: The audit event to log
            
        Returns:
            The ID of the logged event
        """
        if not self.enabled:
            return None
            
        # Convert dict to AuditEvent if needed
        if isinstance(event, dict):
            event = self._dict_to_audit_event(event)
        
        # Add chain hash for tamper evidence
        if self.last_chain_hash:
            chain_input = f"{self.last_chain_hash}:{event.hash}"
            event.details["chain_hash"] = hashlib.sha256(chain_input.encode()).hexdigest()
        
        # Store the event
        event_id = self.storage.store_event(event)
        
        # Update chain hash
        self.last_chain_hash = event.hash
        
        return event_id
    
    def _dict_to_audit_event(self, event_dict: Dict[str, Any]) -> AuditEvent:
        """Convert a dictionary to an AuditEvent object"""
        return AuditEvent(
            event_type=event_dict.get("event_type"),
            action=event_dict.get("action"),
            actor_id=event_dict.get("actor_id"),
            actor_type=event_dict.get("actor_type", "user"),
            resource_id=event_dict.get("resource_id"),
            resource_type=event_dict.get("resource_type"),
            outcome=event_dict.get("outcome", AuditEvent.OUTCOME_SUCCESS),
            details=event_dict.get("details", {}),
            ip_address=event_dict.get("ip_address"),
            user_agent=event_dict.get("user_agent"),
            request_id=event_dict.get("request_id")
        )
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific audit event by ID"""
        return self.storage.get_event(event_id)
    
    def search_events(self, query: Dict[str, Any], start_time=None, end_time=None, 
                    page=1, page_size=50) -> Dict[str, Any]:
        """
        Search for audit events matching specific criteria.
        
        Args:
            query: Search criteria
            start_time: Start of time range to search
            end_time: End of time range to search
            page: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            Dictionary with search results and metadata
        """
        return self.storage.search_events(query, start_time, end_time, page, page_size)
    
    def purge_old_events(self) -> int:
        """Delete events older than the retention period"""
        if not self.retention_days:
            return 0
            
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=self.retention_days)
        return self.storage.delete_events_before(cutoff_date.isoformat() + 'Z')
    
    def verify_integrity(self, start_id=None, end_id=None) -> Dict[str, Any]:
        """
        Verify the integrity of the audit trail by checking event hashes.
        
        Args:
            start_id: Starting event ID for verification
            end_id: Ending event ID for verification
            
        Returns:
            Dictionary with verification results
        """
        events = self.storage.get_events_range(start_id, end_id)
        
        results = {
            "verified": True,
            "total_events": len(events),
            "tampered_events": [],
            "chain_verified": True
        }
        
        previous_hash = None
        
        for event in events:
            # Reconstruct the event data for hash verification
            event_data = {
                "event_id": event["event_id"],
                "timestamp": event["timestamp"],
                "event_type": event["event_type"],
                "action": event["action"],
                "actor_id": event["actor_id"],
                "resource_id": event["resource_id"],
                "outcome": event["outcome"],
                "details": event["details"]
            }
            
            # Convert to stable JSON string (sorted keys)
            json_data = json.dumps(event_data, sort_keys=True)
            
            # Generate verification hash
            verification_hash = hashlib.sha256(json_data.encode()).hexdigest()
            
            # Check if hash matches
            if verification_hash != event["hash"]:
                results["verified"] = False
                results["tampered_events"].append(event["event_id"])
            
            # Verify chain hash if present
            if previous_hash and "chain_hash" in event["details"]:
                chain_input = f"{previous_hash}:{event['hash']}"
                expected_chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
                
                if expected_chain_hash != event["details"]["chain_hash"]:
                    results["chain_verified"] = False
            
            previous_hash = event["hash"]
        
        return results


class DatabaseAuditStorage:
    """Stores audit events in a database"""
    
    def __init__(self, db_connection=None):
        """
        Initialize database storage for audit events.
        
        Args:
            db_connection: Database connection object
        """
        self.db = db_connection
        
        # If no connection provided, we'll use a simple in-memory store for testing
        if not self.db:
            self.events = []
    
    def store_event(self, event: AuditEvent) -> str:
        """Store an audit event in the database"""
        event_dict = event.to_dict()
        
        if not self.db:
            # In-memory storage for testing
            self.events.append(event_dict)
            return event.event_id
        
        # Implement actual database storage here
        # Example using SQLAlchemy would be:
        # new_event = AuditEventModel(**event_dict)
        # db.session.add(new_event)
        # db.session.commit()
        
        return event.event_id
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific audit event by ID"""
        if not self.db:
            # In-memory implementation
            for event in self.events:
                if event["event_id"] == event_id:
                    return event
            return None
        
        # Implement database retrieval here
        # Example using SQLAlchemy:
        # event = AuditEventModel.query.filter_by(event_id=event_id).first()
        # return event.to_dict() if event else None
        
        return None
    
    def search_events(self, query: Dict[str, Any], start_time=None, end_time=None, 
                    page=1, page_size=50) -> Dict[str, Any]:
        """Search for audit events matching specific criteria"""
        if not self.db:
            # In-memory implementation
            results = []
            
            for event in self.events:
                match = True
                
                # Apply query filters
                for key, value in query.items():
                    if key in event:
                        if isinstance(value, list):
                            if event[key] not in value:
                                match = False
                                break
                        elif event[key] != value:
                            match = False
                            break
                
                # Apply time range filter
                if match and start_time and event["timestamp"] < start_time:
                    match = False
                if match and end_time and event["timestamp"] > end_time:
                    match = False
                
                if match:
                    results.append(event)
            
            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_results = results[start_idx:end_idx]
            
            return {
                "events": paginated_results,
                "total": len(results),
                "page": page,
                "page_size": page_size,
                "total_pages": (len(results) + page_size - 1) // page_size
            }
        
        # Implement database search here
        return {"events": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
    
    def delete_events_before(self, timestamp: str) -> int:
        """Delete events older than the given timestamp"""
        if not self.db:
            # In-memory implementation
            original_count = len(self.events)
            self.events = [e for e in self.events if e["timestamp"] >= timestamp]
            return original_count - len(self.events)
        
        # Implement database deletion here
        return 0
    
    def get_events_range(self, start_id=None, end_id=None) -> List[Dict[str, Any]]:
        """Get a range of events for integrity verification"""
        if not self.db:
            # In-memory implementation
            if not start_id and not end_id:
                return self.events.copy()
            
            if start_id and not end_id:
                start_idx = next((i for i, e in enumerate(self.events) if e["event_id"] == start_id), 0)
                return self.events[start_idx:]
            
            if not start_id and end_id:
                end_idx = next((i for i, e in enumerate(self.events) if e["event_id"] == end_id), len(self.events))
                return self.events[:end_idx+1]
            
            start_idx = next((i for i, e in enumerate(self.events) if e["event_id"] == start_id), 0)
            end_idx = next((i for i, e in enumerate(self.events) if e["event_id"] == end_id), len(self.events))
            return self.events[start_idx:end_idx+1]
        
        # Implement database range retrieval here
        return []


# Flask middleware for automatic request auditing
def audit_request_middleware():
    """Middleware to automatically audit API requests"""
    request_start_time = time.time()
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    g.request_id = request_id
    
    # Get user ID if authenticated
    user_id = g.get('user_id', 'anonymous') if hasattr(g, 'user_id') else 'anonymous'
    
    # Create initial audit event
    audit_trail = get_audit_trail()
    
    # We'll complete this event when the request is finished
    g.audit_event = {
        "event_type": AuditEvent.API_USAGE,
        "action": f"{request.method}:{request.path}",
        "actor_id": user_id,
        "resource_id": request.path,
        "resource_type": "api_endpoint",
        "details": {
            "query_params": dict(request.args),
            "headers": {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']},
            "method": request.method,
            "path": request.path
        },
        "request_id": request_id
    }
    
    def after_request(response):
        # Add response data to the audit event
        request_duration = time.time() - request_start_time
        
        # Don't log request/response body for endpoints with sensitive data
        sensitive_endpoints = ['/auth/', '/payment/', '/user/']
        should_log_body = not any(path in request.path for path in sensitive_endpoints)
        
        # Update event details
        g.audit_event["outcome"] = "success" if response.status_code < 400 else "failure"
        g.audit_event["details"]["status_code"] = response.status_code
        g.audit_event["details"]["duration_ms"] = int(request_duration * 1000)
        
        # Log request body for non-sensitive endpoints
        if should_log_body and request.is_json:
            g.audit_event["details"]["request_body"] = request.get_json(silent=True)
        
        # Log response body for non-sensitive endpoints
        if should_log_body and response.is_json:
            try:
                response_json = json.loads(response.get_data(as_text=True))
                g.audit_event["details"]["response_body"] = response_json
            except:
                pass
        
        # Log the completed audit event
        audit_trail.log_event(g.audit_event)
        
        return response
    
    return after_request


def get_audit_trail():
    """Get the global audit trail instance"""
    if not hasattr(g, 'audit_trail'):
        # Create a new audit trail instance if not already in the request context
        g.audit_trail = AuditTrail()
    
    return g.audit_trail


# Helper functions for common audit events
def audit_authentication(user_id, success, details=None):
    """Audit an authentication event"""
    audit_trail = get_audit_trail()
    
    event = AuditEvent(
        event_type=AuditEvent.USER_AUTHENTICATION,
        action="login" if success else "login_failure",
        actor_id=user_id,
        outcome=AuditEvent.OUTCOME_SUCCESS if success else AuditEvent.OUTCOME_FAILURE,
        details=details or {}
    )
    
    return audit_trail.log_event(event)


def audit_authorization(user_id, resource_type, resource_id, action, success, details=None):
    """Audit an authorization event"""
    audit_trail = get_audit_trail()
    
    event = AuditEvent(
        event_type=AuditEvent.USER_AUTHORIZATION,
        action=action,
        actor_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=AuditEvent.OUTCOME_SUCCESS if success else AuditEvent.OUTCOME_FAILURE,
        details=details or {}
    )
    
    return audit_trail.log_event(event)


def audit_data_access(user_id, resource_type, resource_id, details=None):
    """Audit a data access event"""
    audit_trail = get_audit_trail()
    
    event = AuditEvent(
        event_type=AuditEvent.DATA_ACCESS,
        action="view",
        actor_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=AuditEvent.OUTCOME_SUCCESS,
        details=details or {}
    )
    
    return audit_trail.log_event(event)


def audit_data_modification(user_id, resource_type, resource_id, action, details=None):
    """Audit a data modification event"""
    audit_trail = get_audit_trail()
    
    event = AuditEvent(
        event_type=AuditEvent.DATA_MODIFICATION,
        action=action,
        actor_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=AuditEvent.OUTCOME_SUCCESS,
        details=details or {}
    )
    
    return audit_trail.log_event(event)


def audit_security_event(event_name, severity, details=None, actor_id=None):
    """Audit a security-related event"""
    audit_trail = get_audit_trail()

    # Create event details
    event_details = details or {}
    
    # Add severity to the details dictionary
    event_details['severity'] = severity
    
    event = AuditEvent(
        event_type=AuditEvent.SECURITY_EVENT,
        action=event_name,
        actor_id=actor_id or "system",
        actor_type="system" if not actor_id else "user",
        outcome=AuditEvent.OUTCOME_WARNING if severity in ['high', 'critical'] else AuditEvent.OUTCOME_SUCCESS,
        details=event_details
    )
    
    return audit_trail.log_event(event)
