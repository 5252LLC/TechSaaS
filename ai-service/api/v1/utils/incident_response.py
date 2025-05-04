#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Incident Response Management Utility for TechSaaS Platform

This module provides utilities for managing security incidents detected
by the anomaly detection system or reported manually. It supports the
incident lifecycle from creation through resolution.

Author: TechSaaS Security Team
Date: May 4, 2025
"""

import json
import uuid
import logging
import datetime
import os
import threading
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import hashlib

from .anomaly_detection import AnomalyEvent
from ..services.logging_service import LoggingService
from ..services.notification_service import NotificationService, NotificationPriority


class IncidentSeverity(Enum):
    """Classification of incident severity levels."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class IncidentStatus(Enum):
    """Possible states of an incident."""
    NEW = "new"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class IncidentType(Enum):
    """Categories of security incidents."""
    DATA_BREACH = "data_breach"
    ACCOUNT_COMPROMISE = "account_compromise"
    API_ABUSE = "api_abuse"
    INFRASTRUCTURE_ATTACK = "infrastructure_attack"
    MALWARE = "malware"
    DENIAL_OF_SERVICE = "denial_of_service"
    OTHER = "other"


class IncidentEvent:
    """Represents an event in the incident timeline."""
    
    def __init__(self, 
                 event_type: str, 
                 description: str, 
                 user_id: str = None,
                 details: Dict = None):
        """
        Initialize a new incident event.
        
        Args:
            event_type: Type of event (e.g., "detection", "containment")
            description: Human-readable description of the event
            user_id: Identifier of the user who recorded the event
            details: Additional event details
        """
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.now()
        self.event_type = event_type
        self.description = description
        self.user_id = user_id
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        """Convert the event to a dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "description": self.description,
            "user_id": self.user_id,
            "details": self.details
        }


class SecurityIncident:
    """Represents a security incident in the system."""
    
    def __init__(self, 
                 title: str, 
                 description: str, 
                 severity: IncidentSeverity,
                 incident_type: IncidentType,
                 source: str,
                 related_anomaly: AnomalyEvent = None,
                 affected_resources: List[str] = None,
                 affected_users: List[str] = None):
        """
        Initialize a new security incident.
        
        Args:
            title: Short descriptive title
            description: Detailed description of the incident
            severity: Incident severity level
            incident_type: Category of incident
            source: How the incident was detected
            related_anomaly: Associated anomaly event if applicable
            affected_resources: List of affected systems/resources
            affected_users: List of affected user accounts
        """
        self.incident_id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.severity = severity
        self.incident_type = incident_type
        self.status = IncidentStatus.NEW
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at
        self.source = source
        self.related_anomaly_id = related_anomaly.anomaly_id if related_anomaly else None
        self.affected_resources = affected_resources or []
        self.affected_users = affected_users or []
        self.assigned_to = None
        self.events = []
        self.containment_actions = []
        self.evidence_list = []
        
        # Add initial detection event
        self.add_event(
            "detection", 
            f"Incident detected from {source}",
            details={"severity": severity.name, "type": incident_type.name}
        )
    
    def add_event(self, 
                  event_type: str, 
                  description: str, 
                  user_id: str = None, 
                  details: Dict = None) -> IncidentEvent:
        """
        Add an event to the incident timeline.
        
        Args:
            event_type: Type of event
            description: Description of what occurred
            user_id: User who recorded the event
            details: Additional details about the event
            
        Returns:
            The created incident event
        """
        event = IncidentEvent(event_type, description, user_id, details)
        self.events.append(event)
        self.updated_at = event.timestamp
        return event
    
    def update_status(self, 
                     new_status: IncidentStatus, 
                     user_id: str = None, 
                     notes: str = None) -> IncidentEvent:
        """
        Update the incident status.
        
        Args:
            new_status: New status to set
            user_id: User making the change
            notes: Optional notes explaining the status change
            
        Returns:
            The status change event
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.datetime.now()
        
        description = f"Status changed from {old_status.value} to {new_status.value}"
        if notes:
            description += f": {notes}"
            
        return self.add_event("status_change", description, user_id, {
            "old_status": old_status.value,
            "new_status": new_status.value,
            "notes": notes
        })
    
    def assign_to(self, assignee_id: str, assigner_id: str = None) -> IncidentEvent:
        """
        Assign the incident to a team member.
        
        Args:
            assignee_id: User ID of the assignee
            assigner_id: User ID of person making the assignment
            
        Returns:
            The assignment event
        """
        old_assignee = self.assigned_to
        self.assigned_to = assignee_id
        self.updated_at = datetime.datetime.now()
        
        if old_assignee:
            description = f"Reassigned from {old_assignee} to {assignee_id}"
        else:
            description = f"Assigned to {assignee_id}"
            
        return self.add_event("assignment", description, assigner_id, {
            "old_assignee": old_assignee,
            "new_assignee": assignee_id
        })
    
    def add_containment_action(self, 
                              action_type: str, 
                              description: str, 
                              status: str = "pending",
                              user_id: str = None,
                              details: Dict = None) -> Dict:
        """
        Record a containment action.
        
        Args:
            action_type: Type of action taken
            description: Description of the action
            status: Status of the action (pending, completed, failed)
            user_id: User who recorded the action
            details: Additional details about the action
            
        Returns:
            The action record
        """
        action = {
            "action_id": str(uuid.uuid4()),
            "action_type": action_type,
            "description": description,
            "status": status,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "details": details or {}
        }
        
        self.containment_actions.append(action)
        self.updated_at = datetime.datetime.now()
        
        self.add_event("containment_action", 
                      f"Containment action initiated: {description}",
                      user_id,
                      {"action_id": action["action_id"]})
        
        return action
    
    def update_containment_action(self, 
                                 action_id: str, 
                                 status: str, 
                                 notes: str = None,
                                 user_id: str = None) -> Optional[Dict]:
        """
        Update the status of a containment action.
        
        Args:
            action_id: ID of the action to update
            status: New status
            notes: Additional notes about the status update
            user_id: User updating the action
            
        Returns:
            The updated action or None if not found
        """
        for action in self.containment_actions:
            if action["action_id"] == action_id:
                old_status = action["status"]
                action["status"] = status
                action["updated_at"] = datetime.datetime.now().isoformat()
                
                if notes:
                    action["notes"] = notes
                
                self.updated_at = datetime.datetime.now()
                
                description = f"Containment action '{action['description']}' status changed from {old_status} to {status}"
                self.add_event("containment_update", description, user_id, {
                    "action_id": action_id,
                    "old_status": old_status,
                    "new_status": status,
                    "notes": notes
                })
                
                return action
                
        return None
    
    def add_evidence(self, 
                    evidence_type: str, 
                    description: str, 
                    location: str,
                    collector_id: str = None,
                    metadata: Dict = None) -> Dict:
        """
        Record evidence collected during the investigation.
        
        Args:
            evidence_type: Type of evidence
            description: Description of the evidence
            location: Where the evidence is stored
            collector_id: User who collected the evidence
            metadata: Additional metadata about the evidence
            
        Returns:
            The evidence record
        """
        evidence = {
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": evidence_type,
            "description": description,
            "location": location,
            "collected_at": datetime.datetime.now().isoformat(),
            "collector_id": collector_id,
            "chain_of_custody": [{
                "timestamp": datetime.datetime.now().isoformat(),
                "action": "collected",
                "user_id": collector_id,
                "notes": "Initial collection"
            }],
            "metadata": metadata or {}
        }
        
        self.evidence_list.append(evidence)
        self.updated_at = datetime.datetime.now()
        
        self.add_event("evidence_collection", 
                      f"Evidence collected: {description}",
                      collector_id,
                      {"evidence_id": evidence["evidence_id"]})
        
        return evidence
    
    def to_dict(self) -> Dict:
        """Convert the incident to a dictionary representation."""
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.name,
            "incident_type": self.incident_type.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source": self.source,
            "related_anomaly_id": self.related_anomaly_id,
            "affected_resources": self.affected_resources,
            "affected_users": self.affected_users,
            "assigned_to": self.assigned_to,
            "events": [event.to_dict() for event in self.events],
            "containment_actions": self.containment_actions,
            "evidence_list": self.evidence_list
        }


class IncidentManager:
    """
    Manages security incidents for the TechSaaS platform.
    
    This class provides functionality for creating, tracking, and managing
    security incidents through their entire lifecycle.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the incident manager.
        
        Args:
            storage_path: Path to store incident data
        """
        self.logger = LoggingService("security_incidents")
        
        # Set default storage path if not provided
        if storage_path is None:
            base_path = os.environ.get("SECURITY_STORAGE_PATH", "/tmp/techsaas/security")
            self.storage_path = os.path.join(base_path, "incidents")
        else:
            self.storage_path = storage_path
            
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize incident cache
        self.incidents = {}
        self.load_incidents()
        
        # Initialize notification service
        try:
            self.notification_service = NotificationService()
        except Exception as e:
            self.logger.error(f"Failed to initialize notification service: {str(e)}")
            self.notification_service = None
    
    def load_incidents(self):
        """Load existing incidents from storage."""
        try:
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    incident_id = filename.split(".")[0]
                    with open(os.path.join(self.storage_path, filename), 'r') as f:
                        self.incidents[incident_id] = json.load(f)
            
            self.logger.info(f"Loaded {len(self.incidents)} incidents from storage")
        except Exception as e:
            self.logger.error(f"Error loading incidents: {str(e)}")
    
    def save_incident(self, incident: Union[SecurityIncident, Dict]):
        """
        Save an incident to persistent storage.
        
        Args:
            incident: Incident object or dictionary
        """
        try:
            if isinstance(incident, SecurityIncident):
                incident_data = incident.to_dict()
                incident_id = incident.incident_id
            else:
                incident_data = incident
                incident_id = incident["incident_id"]
                
            filepath = os.path.join(self.storage_path, f"{incident_id}.json")
            
            with open(filepath, 'w') as f:
                json.dump(incident_data, f, indent=2)
                
            # Update cache
            self.incidents[incident_id] = incident_data
            
        except Exception as e:
            self.logger.error(f"Error saving incident {incident_id}: {str(e)}")
    
    def create_incident_from_anomaly(self, 
                                    anomaly: AnomalyEvent, 
                                    additional_info: Dict = None) -> SecurityIncident:
        """
        Create a new incident from an anomaly event.
        
        Args:
            anomaly: The anomaly event that triggered the incident
            additional_info: Any additional information to include
            
        Returns:
            The created incident
        """
        # Map anomaly severity to incident severity
        severity_mapping = {
            "critical": IncidentSeverity.CRITICAL,
            "high": IncidentSeverity.HIGH,
            "medium": IncidentSeverity.MEDIUM,
            "low": IncidentSeverity.LOW
        }
        
        # Map anomaly type to incident type
        type_mapping = {
            "access_time": IncidentType.ACCOUNT_COMPROMISE,
            "geo_location": IncidentType.ACCOUNT_COMPROMISE,
            "request_frequency": IncidentType.API_ABUSE,
            "authentication": IncidentType.ACCOUNT_COMPROMISE,
            "data_access": IncidentType.DATA_BREACH
        }
        
        severity = severity_mapping.get(anomaly.severity, IncidentSeverity.MEDIUM)
        incident_type = type_mapping.get(anomaly.anomaly_type, IncidentType.OTHER)
        
        # Create incident
        incident = SecurityIncident(
            title=f"Security incident from {anomaly.anomaly_type} anomaly",
            description=anomaly.description,
            severity=severity,
            incident_type=incident_type,
            source="Anomaly Detection System",
            related_anomaly=anomaly,
            affected_resources=anomaly.affected_resources if hasattr(anomaly, "affected_resources") else [],
            affected_users=[anomaly.user_id] if hasattr(anomaly, "user_id") and anomaly.user_id else []
        )
        
        # Add additional info if provided
        if additional_info:
            for key, value in additional_info.items():
                if hasattr(incident, key):
                    setattr(incident, key, value)
        
        # Save the incident
        self.save_incident(incident)
        
        # Log the incident creation
        self.logger.info(f"Created new incident {incident.incident_id} from anomaly {anomaly.anomaly_id}")
        
        # Send notification based on severity
        if self.notification_service:
            self._send_incident_notification(incident)
        
        return incident
    
    def create_incident(self, 
                       title: str, 
                       description: str, 
                       severity: IncidentSeverity,
                       incident_type: IncidentType,
                       source: str,
                       **kwargs) -> SecurityIncident:
        """
        Create a new security incident manually.
        
        Args:
            title: Incident title
            description: Detailed description
            severity: Incident severity
            incident_type: Type of incident
            source: How the incident was detected
            **kwargs: Additional incident attributes
            
        Returns:
            The created incident
        """
        incident = SecurityIncident(
            title=title,
            description=description,
            severity=severity,
            incident_type=incident_type,
            source=source,
            **kwargs
        )
        
        # Save the incident
        self.save_incident(incident)
        
        # Log the incident creation
        self.logger.info(f"Created new incident {incident.incident_id} manually from {source}")
        
        # Send notification based on severity
        if self.notification_service:
            self._send_incident_notification(incident)
        
        return incident
    
    def get_incident(self, incident_id: str) -> Optional[Dict]:
        """
        Retrieve an incident by ID.
        
        Args:
            incident_id: ID of the incident to retrieve
            
        Returns:
            The incident data or None if not found
        """
        return self.incidents.get(incident_id)
    
    def update_incident(self, 
                       incident_id: str, 
                       updates: Dict,
                       user_id: str = None) -> Optional[Dict]:
        """
        Update an existing incident.
        
        Args:
            incident_id: ID of the incident to update
            updates: Dictionary of fields to update
            user_id: ID of the user making the update
            
        Returns:
            The updated incident or None if not found
        """
        incident = self.get_incident(incident_id)
        if not incident:
            return None
            
        # Special handling for status changes
        if "status" in updates:
            # Log status change event
            old_status = incident["status"]
            new_status = updates["status"]
            
            if old_status != new_status:
                event = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "event_type": "status_change",
                    "description": f"Status changed from {old_status} to {new_status}",
                    "user_id": user_id,
                    "details": {
                        "old_status": old_status,
                        "new_status": new_status
                    }
                }
                
                if "events" not in incident:
                    incident["events"] = []
                    
                incident["events"].append(event)
        
        # Update fields
        for key, value in updates.items():
            incident[key] = value
            
        # Update timestamps
        incident["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save the updated incident
        self.save_incident(incident)
        
        # Log the update
        self.logger.info(f"Updated incident {incident_id}")
        
        return incident
    
    def add_incident_event(self,
                          incident_id: str,
                          event_type: str,
                          description: str,
                          user_id: str = None,
                          details: Dict = None) -> Optional[Dict]:
        """
        Add an event to an incident timeline.
        
        Args:
            incident_id: ID of the incident
            event_type: Type of event
            description: Description of what occurred
            user_id: User who recorded the event
            details: Additional details about the event
            
        Returns:
            The updated incident or None if not found
        """
        incident = self.get_incident(incident_id)
        if not incident:
            return None
            
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "user_id": user_id,
            "details": details or {}
        }
        
        if "events" not in incident:
            incident["events"] = []
            
        incident["events"].append(event)
        incident["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save the updated incident
        self.save_incident(incident)
        
        return incident
    
    def list_incidents(self, 
                      filters: Dict = None, 
                      sort_by: str = "created_at", 
                      sort_order: str = "desc") -> List[Dict]:
        """
        List incidents with optional filtering and sorting.
        
        Args:
            filters: Criteria to filter incidents by
            sort_by: Field to sort by
            sort_order: Sort direction ("asc" or "desc")
            
        Returns:
            List of matching incidents
        """
        results = list(self.incidents.values())
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if key == "time_range":
                    # Time range filter requires special handling
                    start_time = datetime.datetime.fromisoformat(value["start"])
                    end_time = datetime.datetime.fromisoformat(value["end"])
                    
                    results = [
                        incident for incident in results
                        if datetime.datetime.fromisoformat(incident["created_at"]) >= start_time
                        and datetime.datetime.fromisoformat(incident["created_at"]) <= end_time
                    ]
                else:
                    # Standard equality filter
                    results = [
                        incident for incident in results
                        if key in incident and incident[key] == value
                    ]
        
        # Sort results
        if sort_by in ["created_at", "updated_at"]:
            # Parse ISO datetime strings for date-based sorting
            results.sort(
                key=lambda x: datetime.datetime.fromisoformat(x[sort_by]),
                reverse=(sort_order.lower() == "desc")
            )
        else:
            # Standard sorting for other fields
            results.sort(
                key=lambda x: x.get(sort_by, ""),
                reverse=(sort_order.lower() == "desc")
            )
            
        return results
    
    def _send_incident_notification(self, incident: SecurityIncident):
        """
        Send notification about an incident based on severity.
        
        Args:
            incident: The incident to send notification about
        """
        try:
            # Map severity to notification priority
            priority_mapping = {
                IncidentSeverity.CRITICAL: NotificationPriority.URGENT,
                IncidentSeverity.HIGH: NotificationPriority.HIGH,
                IncidentSeverity.MEDIUM: NotificationPriority.MEDIUM,
                IncidentSeverity.LOW: NotificationPriority.LOW
            }
            
            priority = priority_mapping.get(incident.severity, NotificationPriority.MEDIUM)
            
            # Prepare notification content
            subject = f"Security Incident: {incident.title} [{incident.severity.name}]"
            content = (
                f"A new security incident has been detected:\n\n"
                f"ID: {incident.incident_id}\n"
                f"Type: {incident.incident_type.name}\n"
                f"Severity: {incident.severity.name}\n"
                f"Source: {incident.source}\n\n"
                f"Description: {incident.description}\n\n"
                f"Please review this incident in the security dashboard."
            )
            
            # Send to security team group
            recipients = ["security-team"]
            
            # Add individual notifications for high and critical incidents
            if incident.severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
                recipients.extend(["security-oncall", "security-manager"])
                
                # Add executive notification for critical incidents
                if incident.severity == IncidentSeverity.CRITICAL:
                    recipients.append("ciso")
            
            self.notification_service.send_notification(
                recipients=recipients,
                subject=subject,
                content=content,
                priority=priority,
                metadata={
                    "incident_id": incident.incident_id,
                    "severity": incident.severity.name,
                    "type": incident.incident_type.name
                }
            )
            
            self.logger.info(f"Sent incident notification for incident {incident.incident_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send notification for incident {incident.incident_id}: {str(e)}")
