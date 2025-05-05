#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Script for TechSaaS Security Incident Response System

This script tests the functionality of the Incident Response System,
ensuring that it correctly handles incident creation, management,
and integration with the Anomaly Detection System.

Author: TechSaaS Security Team
Date: May 5, 2025
"""

import os
import sys
import json
import unittest
import datetime
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.insert(0, parent_dir)

# Import the incident response components
from api.v1.utils.incident_response import (
    IncidentManager,
    SecurityIncident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType
)
from api.v1.utils.anomaly_detection import AnomalyEvent


class TestIncidentResponse(unittest.TestCase):
    """Test cases for the Incident Response System"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for incident storage
        self.test_dir = tempfile.mkdtemp()
        
        # Initialize incident manager with test directory
        self.incident_manager = IncidentManager(storage_path=self.test_dir)
        
        # Mock the notification service
        self.incident_manager.notification_service = MagicMock()
        
        # Create a sample anomaly for testing
        self.sample_anomaly = AnomalyEvent(
            anomaly_id="test-anomaly-001",
            anomaly_type="access_time",
            description="Unusual login time detected for user admin",
            severity="high",
            timestamp=datetime.datetime.now(),
            source_ip="192.168.1.100",
            user_id="admin",
            details={
                "normal_hours": "9-17",
                "access_time": "03:45"
            }
        )
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_create_incident_manually(self):
        """Test creating an incident manually"""
        # Create incident
        incident = self.incident_manager.create_incident(
            title="Test Security Incident",
            description="This is a test security incident",
            severity=IncidentSeverity.HIGH,
            incident_type=IncidentType.ACCOUNT_COMPROMISE,
            source="Manual Test",
            affected_resources=["server-01", "database-prod"],
            affected_users=["admin", "user1"]
        )
        
        # Verify incident was created correctly
        self.assertIsNotNone(incident)
        self.assertEqual(incident.title, "Test Security Incident")
        self.assertEqual(incident.severity, IncidentSeverity.HIGH)
        self.assertEqual(incident.incident_type, IncidentType.ACCOUNT_COMPROMISE)
        self.assertEqual(incident.status, IncidentStatus.NEW)
        self.assertEqual(len(incident.affected_resources), 2)
        self.assertEqual(len(incident.affected_users), 2)
        
        # Verify initial event was created
        self.assertEqual(len(incident.events), 1)
        self.assertEqual(incident.events[0].event_type, "detection")
    
    def test_create_incident_from_anomaly(self):
        """Test creating an incident from an anomaly"""
        # Create incident from anomaly
        incident = self.incident_manager.create_incident_from_anomaly(
            anomaly=self.sample_anomaly
        )
        
        # Verify incident was created correctly
        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity, IncidentSeverity.HIGH)
        self.assertEqual(incident.incident_type, IncidentType.ACCOUNT_COMPROMISE)
        self.assertEqual(incident.status, IncidentStatus.NEW)
        self.assertEqual(incident.related_anomaly_id, self.sample_anomaly.anomaly_id)
        self.assertEqual(len(incident.affected_users), 1)
        self.assertEqual(incident.affected_users[0], "admin")
        
        # Verify notification was sent
        self.incident_manager.notification_service.send_notification.assert_called_once()
    
    def test_incident_lifecycle(self):
        """Test the complete lifecycle of an incident"""
        # Create incident
        incident = self.incident_manager.create_incident(
            title="Lifecycle Test Incident",
            description="Testing incident lifecycle",
            severity=IncidentSeverity.MEDIUM,
            incident_type=IncidentType.API_ABUSE,
            source="Lifecycle Test"
        )
        
        # Verify incident ID
        incident_id = incident.incident_id
        self.assertIsNotNone(incident_id)
        
        # Add timeline event
        incident.add_event(
            event_type="investigation",
            description="Initial investigation started",
            user_id="security-analyst",
            details={"tool": "log-analyzer"}
        )
        
        # Update incident status
        incident.update_status(
            new_status=IncidentStatus.INVESTIGATING,
            user_id="security-analyst",
            notes="Beginning investigation of suspicious API calls"
        )
        
        # Assign incident
        incident.assign_to(
            assignee_id="john.smith",
            assigner_id="security-manager"
        )
        
        # Add containment action
        action = incident.add_containment_action(
            action_type="api_rate_limit",
            description="Apply stricter rate limiting to affected API endpoints",
            user_id="john.smith"
        )
        
        # Update containment action status
        incident.update_containment_action(
            action_id=action["action_id"],
            status="completed",
            notes="Rate limits applied successfully",
            user_id="john.smith"
        )
        
        # Add evidence
        incident.add_evidence(
            evidence_type="log",
            description="API access logs for suspicious activity",
            location="/var/log/api/access-2025-05-05.log",
            collector_id="john.smith",
            metadata={"size": "1.2MB", "time_range": "02:00-04:00"}
        )
        
        # Update status to resolved
        incident.update_status(
            new_status=IncidentStatus.RESOLVED,
            user_id="john.smith",
            notes="Investigation complete, rate limiting measures implemented"
        )
        
        # Save the incident
        self.incident_manager.save_incident(incident)
        
        # Retrieve the incident and verify
        retrieved = self.incident_manager.get_incident(incident_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["status"], "resolved")
        self.assertEqual(retrieved["assigned_to"], "john.smith")
        self.assertEqual(len(retrieved["events"]), 6)  # Initial + 5 added events
        self.assertEqual(len(retrieved["containment_actions"]), 1)
        self.assertEqual(retrieved["containment_actions"][0]["status"], "completed")
        self.assertEqual(len(retrieved["evidence_list"]), 1)
    
    def test_incident_filtering(self):
        """Test filtering and listing incidents"""
        # Create multiple incidents with different attributes
        incidents = [
            {
                "title": "Critical Data Breach",
                "description": "Customer data exposure",
                "severity": IncidentSeverity.CRITICAL,
                "incident_type": IncidentType.DATA_BREACH,
                "source": "Monitoring System"
            },
            {
                "title": "API Rate Limit Abuse",
                "description": "Excessive API calls from single IP",
                "severity": IncidentSeverity.MEDIUM,
                "incident_type": IncidentType.API_ABUSE,
                "source": "API Gateway"
            },
            {
                "title": "Suspicious Login Attempt",
                "description": "Multiple failed logins from unusual location",
                "severity": IncidentSeverity.HIGH,
                "incident_type": IncidentType.ACCOUNT_COMPROMISE,
                "source": "Authentication System"
            }
        ]
        
        # Create the incidents
        for inc_data in incidents:
            incident = self.incident_manager.create_incident(**inc_data)
            if inc_data["title"] == "API Rate Limit Abuse":
                # Mark this one as resolved to test status filtering
                incident.update_status(IncidentStatus.RESOLVED, "security-analyst")
                self.incident_manager.save_incident(incident)
        
        # Test filtering by severity
        critical_incidents = self.incident_manager.list_incidents(
            filters={"severity": "CRITICAL"},
            sort_by="created_at"
        )
        self.assertEqual(len(critical_incidents), 1)
        self.assertEqual(critical_incidents[0]["title"], "Critical Data Breach")
        
        # Test filtering by status
        resolved_incidents = self.incident_manager.list_incidents(
            filters={"status": "resolved"},
            sort_by="created_at"
        )
        self.assertEqual(len(resolved_incidents), 1)
        self.assertEqual(resolved_incidents[0]["title"], "API Rate Limit Abuse")
        
        # Test filtering by type
        account_incidents = self.incident_manager.list_incidents(
            filters={"incident_type": "ACCOUNT_COMPROMISE"},
            sort_by="created_at"
        )
        self.assertEqual(len(account_incidents), 1)
        self.assertEqual(account_incidents[0]["title"], "Suspicious Login Attempt")
        
        # Test sorting by severity (descending)
        all_incidents = self.incident_manager.list_incidents(
            sort_by="severity",
            sort_order="desc"
        )
        self.assertEqual(len(all_incidents), 3)
        self.assertEqual(all_incidents[0]["severity"], "CRITICAL")
        self.assertEqual(all_incidents[1]["severity"], "HIGH")


class TestIncidentResponseAPI(unittest.TestCase):
    """Test cases for the Incident Response API endpoints"""
    
    @patch('api.v1.routes.incident_response.incident_manager')
    def test_create_incident_api(self, mock_manager):
        """Test the create incident API endpoint"""
        from api.v1.routes.incident_response import incident_blueprint
        from flask import Flask, json
        
        # Create a test Flask app
        app = Flask(__name__)
        app.register_blueprint(incident_blueprint)
        app.testing = True
        
        # Mock the create_incident method
        mock_incident = MagicMock()
        mock_incident.incident_id = "test-incident-001"
        mock_incident.to_dict.return_value = {
            "incident_id": "test-incident-001",
            "title": "API Test Incident",
            "severity": "HIGH",
            "status": "new"
        }
        mock_manager.create_incident.return_value = mock_incident
        
        # Test the endpoint
        with app.test_client() as client:
            response = client.post(
                '/api/v1/security/incidents',
                json={
                    "title": "API Test Incident",
                    "description": "Testing incident API",
                    "severity": "HIGH",
                    "incident_type": "API_ABUSE",
                    "source": "API Test"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify response
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["incident"]["incident_id"], "test-incident-001")
            
            # Verify manager was called correctly
            mock_manager.create_incident.assert_called_once()


if __name__ == "__main__":
    # Run the test suite
    unittest.main()
