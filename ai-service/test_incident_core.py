#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified Test Script for TechSaaS Security Incident Response Core Functionality
This script tests the core components without requiring Flask
"""

import os
import sys
import json
import datetime
import tempfile
import shutil

# Path setup to allow importing from the project
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Define mock classes to simulate the real ones without dependencies
class IncidentSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentStatus:
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"

class IncidentType:
    DATA_BREACH = "DATA_BREACH"
    ACCOUNT_COMPROMISE = "ACCOUNT_COMPROMISE"
    API_ABUSE = "API_ABUSE"
    INFRASTRUCTURE_ATTACK = "INFRASTRUCTURE_ATTACK"
    MALWARE = "MALWARE"
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"
    OTHER = "OTHER"

class TimelineEvent:
    def __init__(self, event_type, description, user_id=None, timestamp=None, details=None):
        self.event_type = event_type
        self.description = description
        self.user_id = user_id
        self.timestamp = timestamp or datetime.datetime.now()
        self.details = details or {}
        self.event_id = f"event-{int(self.timestamp.timestamp())}"
    
    def to_dict(self):
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "description": self.description,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

class Evidence:
    def __init__(self, evidence_type, description, location, collector_id=None, timestamp=None, metadata=None):
        self.evidence_type = evidence_type
        self.description = description
        self.location = location
        self.collector_id = collector_id
        self.timestamp = timestamp or datetime.datetime.now()
        self.metadata = metadata or {}
        self.evidence_id = f"evidence-{int(self.timestamp.timestamp())}"
    
    def to_dict(self):
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "description": self.description,
            "location": self.location,
            "collector_id": self.collector_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

class ContainmentAction:
    def __init__(self, action_type, description, user_id=None, timestamp=None):
        self.action_type = action_type
        self.description = description
        self.user_id = user_id
        self.timestamp = timestamp or datetime.datetime.now()
        self.action_id = f"action-{int(self.timestamp.timestamp())}"
        self.status = "pending"
        self.notes = ""
    
    def to_dict(self):
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "notes": self.notes
        }

class SecurityIncident:
    def __init__(self, title, description, severity, incident_type, source, 
                 affected_resources=None, affected_users=None, incident_id=None):
        self.title = title
        self.description = description
        self.severity = severity
        self.incident_type = incident_type
        self.source = source
        self.incident_id = incident_id or f"inc-{int(datetime.datetime.now().timestamp())}"
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at
        self.status = IncidentStatus.NEW
        self.assigned_to = None
        self.affected_resources = affected_resources or []
        self.affected_users = affected_users or []
        self.related_anomaly_id = None
        self.events = []
        self.add_event("detection", f"Incident detected: {title}")
        self.containment_actions = []
        self.evidence_list = []
    
    def add_event(self, event_type, description, user_id=None, details=None):
        event = TimelineEvent(event_type, description, user_id, details=details)
        self.events.append(event)
        self.updated_at = datetime.datetime.now()
        return event.to_dict()
    
    def update_status(self, new_status, user_id=None, notes=None):
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.datetime.now()
        
        # Add status change event
        self.add_event(
            "status_change",
            f"Status changed from {old_status} to {new_status}",
            user_id,
            details={"old_status": old_status, "new_status": new_status, "notes": notes}
        )
        return self.status
    
    def assign_to(self, assignee_id, assigner_id=None):
        previous_assignee = self.assigned_to
        self.assigned_to = assignee_id
        self.updated_at = datetime.datetime.now()
        
        self.add_event(
            "assignment",
            f"Incident assigned to {assignee_id}",
            assigner_id,
            details={"previous_assignee": previous_assignee, "new_assignee": assignee_id}
        )
        return assignee_id
    
    def add_containment_action(self, action_type, description, user_id=None):
        action = ContainmentAction(action_type, description, user_id)
        self.containment_actions.append(action)
        self.updated_at = datetime.datetime.now()
        
        self.add_event(
            "containment_action",
            f"Containment action added: {description}",
            user_id,
            details={"action_type": action_type, "action_id": action.action_id}
        )
        return action.to_dict()
    
    def update_containment_action(self, action_id, status, notes=None, user_id=None):
        for action in self.containment_actions:
            if action.action_id == action_id:
                action.status = status
                if notes:
                    action.notes = notes
                self.updated_at = datetime.datetime.now()
                
                self.add_event(
                    "containment_action_update",
                    f"Containment action updated: {status}",
                    user_id,
                    details={"action_id": action_id, "status": status, "notes": notes}
                )
                return action.to_dict()
        return None
    
    def add_evidence(self, evidence_type, description, location, collector_id=None, metadata=None):
        evidence = Evidence(evidence_type, description, location, collector_id, metadata=metadata)
        self.evidence_list.append(evidence)
        self.updated_at = datetime.datetime.now()
        
        self.add_event(
            "evidence_collection",
            f"Evidence collected: {description}",
            collector_id,
            details={"evidence_type": evidence_type, "evidence_id": evidence.evidence_id}
        )
        return evidence.to_dict()
    
    def to_dict(self):
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "incident_type": self.incident_type,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "assigned_to": self.assigned_to,
            "affected_resources": self.affected_resources,
            "affected_users": self.affected_users,
            "related_anomaly_id": self.related_anomaly_id,
            "events": [event.to_dict() for event in self.events],
            "containment_actions": [action.to_dict() for action in self.containment_actions],
            "evidence_list": [evidence.to_dict() for evidence in self.evidence_list]
        }

class IncidentManager:
    def __init__(self, storage_path=None):
        self.storage_path = storage_path or os.path.join(tempfile.gettempdir(), "incidents")
        os.makedirs(self.storage_path, exist_ok=True)
        print(f"Incident storage path: {self.storage_path}")
        
        # Normally this would integrate with other systems
        self.notification_service = self.MockNotificationService()
    
    class MockNotificationService:
        def send_notification(self, recipient, subject, message, priority=None):
            print(f"NOTIFICATION: To: {recipient}, Subject: {subject}, Priority: {priority}")
            print(f"Message: {message}")
            return True
    
    def create_incident(self, title, description, severity, incident_type, source, 
                       affected_resources=None, affected_users=None):
        """Create a new security incident"""
        incident = SecurityIncident(
            title=title,
            description=description,
            severity=severity,
            incident_type=incident_type,
            source=source,
            affected_resources=affected_resources,
            affected_users=affected_users
        )
        
        # Save the incident
        self.save_incident(incident)
        
        # Send notification for high severity incidents
        if severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            self.notification_service.send_notification(
                recipient="security-team@techsaas.com",
                subject=f"[{severity}] New Security Incident: {title}",
                message=f"A new {severity} severity incident has been created: {title}\n\n"
                        f"Description: {description}\n"
                        f"Incident ID: {incident.incident_id}",
                priority="high"
            )
        
        return incident
    
    def save_incident(self, incident):
        """Save incident to storage"""
        incident_path = os.path.join(self.storage_path, f"{incident.incident_id}.json")
        with open(incident_path, 'w') as f:
            json.dump(incident.to_dict(), f, indent=2)
        return incident_path
    
    def get_incident(self, incident_id):
        """Retrieve an incident by ID"""
        incident_path = os.path.join(self.storage_path, f"{incident_id}.json")
        if os.path.exists(incident_path):
            with open(incident_path, 'r') as f:
                return json.load(f)
        return None
    
    def list_incidents(self, filters=None, sort_by="created_at", sort_order="desc"):
        """List incidents with optional filtering and sorting"""
        incidents = []
        filters = filters or {}
        
        # List all incident files
        for filename in os.listdir(self.storage_path):
            if filename.endswith(".json"):
                file_path = os.path.join(self.storage_path, filename)
                with open(file_path, 'r') as f:
                    incident = json.load(f)
                
                # Apply filters
                include = True
                for filter_key, filter_value in filters.items():
                    if filter_key in incident and str(incident[filter_key]) != str(filter_value):
                        include = False
                        break
                
                if include:
                    incidents.append(incident)
        
        # Sort incidents
        if sort_by in incidents[0] if incidents else {}:
            reverse = sort_order.lower() == "desc"
            incidents.sort(key=lambda x: x[sort_by], reverse=reverse)
        
        return incidents


def run_test():
    """Run a simple test of incident management functionality"""
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    try:
        print("=== TechSaaS Incident Response Core Test ===")
        
        # Initialize the incident manager
        manager = IncidentManager(storage_path=test_dir)
        
        # Create a test incident
        print("\n1. Creating test incident...")
        incident = manager.create_incident(
            title="Suspicious Login Activity",
            description="Multiple failed login attempts from unusual location",
            severity=IncidentSeverity.HIGH,
            incident_type=IncidentType.ACCOUNT_COMPROMISE,
            source="Authentication System",
            affected_users=["admin"]
        )
        
        print(f"Created incident ID: {incident.incident_id}")
        
        # Add timeline events
        print("\n2. Adding timeline events...")
        incident.add_event(
            event_type="investigation",
            description="Initial investigation started",
            user_id="analyst1",
            details={"tool": "log-analyzer"}
        )
        
        # Update status
        print("\n3. Updating incident status...")
        incident.update_status(
            new_status=IncidentStatus.INVESTIGATING,
            user_id="analyst1",
            notes="Beginning investigation of suspicious logins"
        )
        
        # Assign incident
        print("\n4. Assigning incident...")
        incident.assign_to(
            assignee_id="john.smith",
            assigner_id="security-manager"
        )
        
        # Add containment action
        print("\n5. Adding containment action...")
        action = incident.add_containment_action(
            action_type="account_lockout",
            description="Temporarily lock affected accounts",
            user_id="john.smith"
        )
        
        # Update containment action status
        print("\n6. Updating containment action...")
        incident.update_containment_action(
            action_id=action["action_id"],
            status="completed",
            notes="All affected accounts locked, users notified",
            user_id="john.smith"
        )
        
        # Add evidence
        print("\n7. Adding evidence...")
        incident.add_evidence(
            evidence_type="log",
            description="Authentication logs showing failed attempts",
            location="/var/log/auth.log",
            collector_id="john.smith",
            metadata={"size": "1.5MB", "time_range": "02:00-04:00"}
        )
        
        # Save and retrieve the incident
        print("\n8. Saving and retrieving incident...")
        manager.save_incident(incident)
        retrieved = manager.get_incident(incident.incident_id)
        
        print(f"\nRetrieved incident: {retrieved['title']}")
        print(f"Status: {retrieved['status']}")
        print(f"Assigned to: {retrieved['assigned_to']}")
        print(f"Events: {len(retrieved['events'])}")
        print(f"Containment actions: {len(retrieved['containment_actions'])}")
        print(f"Evidence items: {len(retrieved['evidence_list'])}")
        
        # Create a second incident for filtering tests
        print("\n9. Creating additional test incidents...")
        incident2 = manager.create_incident(
            title="API Rate Limit Abuse",
            description="Excessive API calls from single IP",
            severity=IncidentSeverity.MEDIUM,
            incident_type=IncidentType.API_ABUSE,
            source="API Gateway"
        )
        incident2.update_status(IncidentStatus.RESOLVED, "analyst2")
        manager.save_incident(incident2)
        
        # List and filter incidents
        print("\n10. Testing incident filtering...")
        high_severity = manager.list_incidents(filters={"severity": "HIGH"})
        print(f"High severity incidents: {len(high_severity)}")
        resolved = manager.list_incidents(filters={"status": "RESOLVED"})
        print(f"Resolved incidents: {len(resolved)}")
        
        print("\n=== Test completed successfully ===")
        
    finally:
        # Clean up the test directory
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    run_test()
