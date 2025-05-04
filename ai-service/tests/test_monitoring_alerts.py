"""
Tests for the Monitoring Alerts System

This module contains tests for the alerts management and notification
functionality of the TechSaaS monitoring system.
"""

import unittest
import time
import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock, call

from api.v1.utils.monitoring.alerts import (
    AlertRule,
    Alert,
    AlertManager,
    initialize_alerts,
    add_alert_rule,
    update_alert_rule,
    delete_alert_rule,
    get_alert_rules,
    get_alerts,
    acknowledge_alert,
    resolve_alert,
    check_alert_thresholds,
    send_alert,
    email_alert_handler,
    webhook_alert_handler,
    slack_alert_handler,
    STATUS_ACTIVE,
    STATUS_ACKNOWLEDGED,
    STATUS_RESOLVED,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SEVERITY_ERROR,
    SEVERITY_CRITICAL
)
from api.v1.utils.monitoring.metrics import Metric


class TestAlertClasses(unittest.TestCase):
    """Tests for the alert data classes."""
    
    def test_alert_rule(self):
        """Test the AlertRule class."""
        rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        
        self.assertEqual(rule.id, "rule1")
        self.assertEqual(rule.name, "High CPU Usage")
        self.assertEqual(rule.description, "Alert when CPU usage is too high")
        self.assertEqual(rule.metric_type, "system")
        self.assertEqual(rule.metric_name, "cpu_usage")
        self.assertEqual(rule.condition, "gt")
        self.assertEqual(rule.threshold, 80.0)
        self.assertEqual(rule.severity, SEVERITY_WARNING)
        self.assertTrue(rule.enabled)
        
        # Test conversion to dict
        rule_dict = rule.to_dict()
        self.assertEqual(rule_dict["id"], "rule1")
        self.assertEqual(rule_dict["name"], "High CPU Usage")
        self.assertEqual(rule_dict["description"], "Alert when CPU usage is too high")
        self.assertEqual(rule_dict["metric_type"], "system")
        self.assertEqual(rule_dict["metric_name"], "cpu_usage")
        self.assertEqual(rule_dict["condition"], "gt")
        self.assertEqual(rule_dict["threshold"], 80.0)
        self.assertEqual(rule_dict["severity"], SEVERITY_WARNING)
        self.assertTrue(rule_dict["enabled"])
        
        # Test from_dict
        new_rule = AlertRule.from_dict(rule_dict)
        self.assertEqual(new_rule.id, rule.id)
        self.assertEqual(new_rule.name, rule.name)
        self.assertEqual(new_rule.description, rule.description)
        self.assertEqual(new_rule.metric_type, rule.metric_type)
        self.assertEqual(new_rule.metric_name, rule.metric_name)
        self.assertEqual(new_rule.condition, rule.condition)
        self.assertEqual(new_rule.threshold, rule.threshold)
        self.assertEqual(new_rule.severity, rule.severity)
        self.assertEqual(new_rule.enabled, rule.enabled)
    
    def test_alert(self):
        """Test the Alert class."""
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        self.assertEqual(alert.id, "alert1")
        self.assertEqual(alert.rule_id, "rule1")
        self.assertEqual(alert.name, "High CPU Usage")
        self.assertEqual(alert.description, "CPU usage above threshold")
        self.assertEqual(alert.metric_type, "system")
        self.assertEqual(alert.metric_name, "cpu_usage")
        self.assertEqual(alert.condition, "gt")
        self.assertEqual(alert.threshold, 80.0)
        self.assertEqual(alert.actual_value, 85.0)
        self.assertEqual(alert.severity, SEVERITY_WARNING)
        self.assertEqual(alert.status, STATUS_ACTIVE)
        self.assertIsNotNone(alert.created_at)
        self.assertIsNotNone(alert.updated_at)
        self.assertIsNone(alert.acknowledged_at)
        self.assertIsNone(alert.resolved_at)
        self.assertEqual(alert.acknowledged_by, "")
        
        # Test conversion to dict
        alert_dict = alert.to_dict()
        self.assertEqual(alert_dict["id"], "alert1")
        self.assertEqual(alert_dict["rule_id"], "rule1")
        self.assertEqual(alert_dict["name"], "High CPU Usage")
        self.assertEqual(alert_dict["description"], "CPU usage above threshold")
        self.assertEqual(alert_dict["metric_type"], "system")
        self.assertEqual(alert_dict["metric_name"], "cpu_usage")
        self.assertEqual(alert_dict["condition"], "gt")
        self.assertEqual(alert_dict["threshold"], 80.0)
        self.assertEqual(alert_dict["actual_value"], 85.0)
        self.assertEqual(alert_dict["severity"], SEVERITY_WARNING)
        self.assertEqual(alert_dict["status"], STATUS_ACTIVE)
        
        # Test from_dict
        new_alert = Alert.from_dict(alert_dict)
        self.assertEqual(new_alert.id, alert.id)
        self.assertEqual(new_alert.rule_id, alert.rule_id)
        self.assertEqual(new_alert.name, alert.name)
        self.assertEqual(new_alert.description, alert.description)
        self.assertEqual(new_alert.metric_type, alert.metric_type)
        self.assertEqual(new_alert.metric_name, alert.metric_name)
        self.assertEqual(new_alert.condition, alert.condition)
        self.assertEqual(new_alert.threshold, alert.threshold)
        self.assertEqual(new_alert.actual_value, alert.actual_value)
        self.assertEqual(new_alert.severity, alert.severity)
        self.assertEqual(new_alert.status, alert.status)


class TestAlertManager(unittest.TestCase):
    """Tests for the AlertManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.alert_manager = AlertManager()
        self.alert_manager.initialize(storage_path=self.temp_dir)
        
        # Add a test rule
        self.rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        self.alert_manager.add_rule(self.rule)
    
    def tearDown(self):
        """Clean up after tests."""
        self.alert_manager.shutdown()
        shutil.rmtree(self.temp_dir)
    
    def test_add_rule(self):
        """Test adding a rule."""
        rule = AlertRule(
            id="rule2",
            name="High Memory Usage",
            description="Alert when memory usage is too high",
            metric_type="system",
            metric_name="memory_usage",
            condition="gt",
            threshold=90.0,
            severity=SEVERITY_ERROR
        )
        self.alert_manager.add_rule(rule)
        
        # Check if rule was added
        stored_rule = self.alert_manager.get_rule("rule2")
        self.assertIsNotNone(stored_rule)
        self.assertEqual(stored_rule.name, "High Memory Usage")
        self.assertEqual(stored_rule.threshold, 90.0)
    
    def test_update_rule(self):
        """Test updating a rule."""
        # Update the rule
        updated_rule = self.alert_manager.update_rule(
            "rule1",
            name="Updated CPU Alert",
            threshold=85.0,
            severity=SEVERITY_ERROR
        )
        
        # Check if rule was updated
        self.assertIsNotNone(updated_rule)
        self.assertEqual(updated_rule.name, "Updated CPU Alert")
        self.assertEqual(updated_rule.threshold, 85.0)
        self.assertEqual(updated_rule.severity, SEVERITY_ERROR)
        
        # Check if stored rule was updated
        stored_rule = self.alert_manager.get_rule("rule1")
        self.assertEqual(stored_rule.name, "Updated CPU Alert")
        self.assertEqual(stored_rule.threshold, 85.0)
        self.assertEqual(stored_rule.severity, SEVERITY_ERROR)
    
    def test_delete_rule(self):
        """Test deleting a rule."""
        # Delete the rule
        result = self.alert_manager.delete_rule("rule1")
        
        # Check if rule was deleted
        self.assertTrue(result)
        self.assertIsNone(self.alert_manager.get_rule("rule1"))
    
    def test_get_rules(self):
        """Test getting all rules."""
        # Add another rule
        rule = AlertRule(
            id="rule2",
            name="High Memory Usage",
            description="Alert when memory usage is too high",
            metric_type="system",
            metric_name="memory_usage",
            condition="gt",
            threshold=90.0,
            severity=SEVERITY_ERROR
        )
        self.alert_manager.add_rule(rule)
        
        # Get all rules
        rules = self.alert_manager.get_rules()
        
        # Check results
        self.assertEqual(len(rules), 2)
        rule_ids = [r.id for r in rules]
        self.assertIn("rule1", rule_ids)
        self.assertIn("rule2", rule_ids)
        
        # Test enabled_only
        disabled_rule = AlertRule(
            id="rule3",
            name="Disabled Rule",
            description="This rule is disabled",
            metric_type="system",
            metric_name="disk_usage",
            condition="gt",
            threshold=95.0,
            enabled=False
        )
        self.alert_manager.add_rule(disabled_rule)
        
        # Get enabled rules only
        enabled_rules = self.alert_manager.get_rules(enabled_only=True)
        self.assertEqual(len(enabled_rules), 2)
        rule_ids = [r.id for r in enabled_rules]
        self.assertNotIn("rule3", rule_ids)
    
    @patch("api.v1.utils.monitoring.metrics.get_metric_summary")
    def test_check_alert_rules(self, mock_get_summary):
        """Test checking alert rules against metrics."""
        # Mock the metrics summary
        mock_get_summary.return_value = {
            "cpu_usage": {
                "avg": 85.0,
                "max": 90.0,
                "min": 80.0,
                "count": 5
            }
        }
        
        # Check rules
        alerts = self.alert_manager.check_alert_rules()
        
        # Check results
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule_id, "rule1")
        self.assertEqual(alerts[0].name, "High CPU Usage")
        self.assertEqual(alerts[0].actual_value, 85.0)
        self.assertEqual(alerts[0].status, STATUS_ACTIVE)
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        # Create an alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # Add the alert to the manager
        self.alert_manager._alerts["alert1"] = alert
        
        # Acknowledge the alert
        updated_alert = self.alert_manager.acknowledge_alert("alert1", "admin")
        
        # Check if alert was acknowledged
        self.assertIsNotNone(updated_alert)
        self.assertEqual(updated_alert.status, STATUS_ACKNOWLEDGED)
        self.assertEqual(updated_alert.acknowledged_by, "admin")
        self.assertIsNotNone(updated_alert.acknowledged_at)
        
        # Check if stored alert was updated
        stored_alert = self.alert_manager.get_alert("alert1")
        self.assertEqual(stored_alert.status, STATUS_ACKNOWLEDGED)
        self.assertEqual(stored_alert.acknowledged_by, "admin")
    
    def test_resolve_alert(self):
        """Test resolving an alert."""
        # Create an alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # Add the alert to the manager
        self.alert_manager._alerts["alert1"] = alert
        
        # Resolve the alert
        updated_alert = self.alert_manager.resolve_alert("alert1")
        
        # Check if alert was resolved
        self.assertIsNotNone(updated_alert)
        self.assertEqual(updated_alert.status, STATUS_RESOLVED)
        self.assertIsNotNone(updated_alert.resolved_at)
        
        # Check if stored alert was updated
        stored_alert = self.alert_manager.get_alert("alert1")
        self.assertEqual(stored_alert.status, STATUS_RESOLVED)
    
    def test_get_alerts(self):
        """Test getting alerts with filters."""
        # Create and add multiple alerts
        alert1 = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        alert2 = Alert(
            id="alert2",
            rule_id="rule2",
            name="High Memory Usage",
            description="Memory usage above threshold",
            metric_type="system",
            metric_name="memory_usage",
            condition="gt",
            threshold=90.0,
            actual_value=95.0,
            severity=SEVERITY_ERROR
        )
        
        self.alert_manager._alerts["alert1"] = alert1
        self.alert_manager._alerts["alert2"] = alert2
        
        # Test getting all alerts
        alerts = self.alert_manager.get_alerts()
        self.assertEqual(len(alerts), 2)
        
        # Test filtering by status
        alert2.status = STATUS_RESOLVED
        alerts = self.alert_manager.get_alerts(status=STATUS_ACTIVE)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].id, "alert1")
        
        # Test filtering by severity
        alerts = self.alert_manager.get_alerts(severity=SEVERITY_ERROR)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].id, "alert2")
        
        # Test filtering by rule_id
        alerts = self.alert_manager.get_alerts(rule_id="rule1")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].id, "alert1")
        
        # Test limit
        alerts = self.alert_manager.get_alerts(limit=1)
        self.assertEqual(len(alerts), 1)
    
    def test_register_alert_handler(self):
        """Test registering an alert handler."""
        # Create a mock handler
        mock_handler = MagicMock()
        
        # Register the handler
        self.alert_manager.register_alert_handler(mock_handler)
        
        # Create an alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # Check if handler is called when alert is triggered
        self.alert_manager._alerts = {}  # Clear existing alerts
        
        with patch("api.v1.utils.monitoring.metrics.get_metric_summary") as mock_get_summary:
            # Mock the metrics summary
            mock_get_summary.return_value = {
                "cpu_usage": {
                    "avg": 85.0,
                    "max": 90.0,
                    "min": 80.0,
                    "count": 5
                }
            }
            
            # Check rules
            self.alert_manager.check_alert_rules()
            
            # Check if handler was called
            mock_handler.assert_called_once()
            called_alert = mock_handler.call_args[0][0]
            self.assertEqual(called_alert.rule_id, "rule1")
            self.assertEqual(called_alert.name, "High CPU Usage")


class TestPublicAPI(unittest.TestCase):
    """Tests for the public API functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        initialize_alerts(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_alert_rule(self):
        """Test adding an alert rule."""
        rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        
        add_alert_rule(rule)
        
        # Check if rule was added
        rules = get_alert_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["id"], "rule1")
        self.assertEqual(rules[0]["name"], "High CPU Usage")
    
    def test_update_alert_rule(self):
        """Test updating an alert rule."""
        # First add a rule
        rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        
        add_alert_rule(rule)
        
        # Update the rule
        updated_rule = update_alert_rule(
            "rule1",
            name="Updated CPU Alert",
            threshold=85.0,
            severity=SEVERITY_ERROR
        )
        
        # Check if rule was updated
        self.assertEqual(updated_rule["name"], "Updated CPU Alert")
        self.assertEqual(updated_rule["threshold"], 85.0)
        self.assertEqual(updated_rule["severity"], SEVERITY_ERROR)
        
        # Check if stored rule was updated
        rules = get_alert_rules()
        self.assertEqual(rules[0]["name"], "Updated CPU Alert")
        self.assertEqual(rules[0]["threshold"], 85.0)
        self.assertEqual(rules[0]["severity"], SEVERITY_ERROR)
    
    def test_delete_alert_rule(self):
        """Test deleting an alert rule."""
        # First add a rule
        rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        
        add_alert_rule(rule)
        
        # Delete the rule
        result = delete_alert_rule("rule1")
        
        # Check if rule was deleted
        self.assertTrue(result)
        rules = get_alert_rules()
        self.assertEqual(len(rules), 0)
    
    @patch("api.v1.utils.monitoring.metrics.get_metric_summary")
    def test_check_alert_thresholds(self, mock_get_summary):
        """Test checking alert thresholds."""
        # Add a rule
        rule = AlertRule(
            id="rule1",
            name="High CPU Usage",
            description="Alert when CPU usage is too high",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            severity=SEVERITY_WARNING
        )
        
        add_alert_rule(rule)
        
        # Mock the metrics summary
        mock_get_summary.return_value = {
            "cpu_usage": {
                "avg": 85.0,
                "max": 90.0,
                "min": 80.0,
                "count": 5
            }
        }
        
        # Check thresholds
        alerts = check_alert_thresholds()
        
        # Check results
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["rule_id"], "rule1")
        self.assertEqual(alerts[0]["name"], "High CPU Usage")
        self.assertEqual(alerts[0]["actual_value"], 85.0)
        self.assertEqual(alerts[0]["status"], STATUS_ACTIVE)
    
    def test_send_alert(self):
        """Test manually sending an alert."""
        # Send an alert
        alert = send_alert(
            alert_type="test",
            name="Test Alert",
            description="This is a test alert",
            severity=SEVERITY_INFO,
            metric_type="system",
            metric_name="test_metric",
            value=42.0
        )
        
        # Check if alert was created
        self.assertEqual(alert["name"], "Test Alert")
        self.assertEqual(alert["description"], "This is a test alert")
        self.assertEqual(alert["severity"], SEVERITY_INFO)
        self.assertEqual(alert["metric_type"], "system")
        self.assertEqual(alert["metric_name"], "test_metric")
        self.assertEqual(alert["actual_value"], 42.0)
        self.assertEqual(alert["status"], STATUS_ACTIVE)
        
        # Check if alert was stored
        alerts = get_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["name"], "Test Alert")
    
    @patch("smtplib.SMTP")
    def test_email_alert_handler(self, mock_smtp):
        """Test email alert handler."""
        # Create alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # SMTP config
        smtp_config = {
            "server": "smtp.example.com",
            "port": 587,
            "username": "test",
            "password": "password",
            "from_email": "alerts@example.com",
            "to_email": "admin@example.com"
        }
        
        # Call handler
        email_alert_handler(alert, smtp_config)
        
        # Check if SMTP was called correctly
        mock_smtp.assert_called_with("smtp.example.com", 587)
        mock_smtp_instance = mock_smtp.return_value
        mock_smtp_instance.login.assert_called_with("test", "password")
        mock_smtp_instance.send_message.assert_called_once()
    
    @patch("requests.post")
    def test_webhook_alert_handler(self, mock_post):
        """Test webhook alert handler."""
        # Create alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # Webhook URL
        webhook_url = "https://hooks.example.com/alert"
        
        # Call handler
        webhook_alert_handler(alert, webhook_url)
        
        # Check if requests.post was called correctly
        mock_post.assert_called_with(
            webhook_url,
            json=alert.to_dict(),
            headers={"Content-Type": "application/json"}
        )
    
    @patch("requests.post")
    def test_slack_alert_handler(self, mock_post):
        """Test Slack alert handler."""
        # Create alert
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            name="High CPU Usage",
            description="CPU usage above threshold",
            metric_type="system",
            metric_name="cpu_usage",
            condition="gt",
            threshold=80.0,
            actual_value=85.0,
            severity=SEVERITY_WARNING
        )
        
        # Slack webhook URL
        webhook_url = "https://hooks.slack.com/services/xxx/yyy/zzz"
        
        # Call handler
        slack_alert_handler(alert, webhook_url)
        
        # Check if requests.post was called correctly
        mock_post.assert_called_with(
            webhook_url,
            json={"blocks": mock_post.call_args[1]["json"]["blocks"]},
            headers={"Content-Type": "application/json"}
        )
        
        # Check that the payload contains alert info
        blocks = mock_post.call_args[1]["json"]["blocks"]
        block_text = blocks[0]["text"]["text"]
        self.assertIn("High CPU Usage", block_text)
        self.assertIn("WARNING", block_text)


if __name__ == "__main__":
    unittest.main()
