"""
Tests for the Monitoring System Integration

This module contains tests for the integration functionality that connects
the monitoring system with the main Flask application and other components.
"""

import unittest
import tempfile
import shutil
import time
import os
import json
from unittest.mock import patch, MagicMock, call

from flask import Flask, Response, request, g
import pytest
from werkzeug.test import EnvironBuilder

from api.v1.utils.monitoring.integration import (
    RequestMonitoringMiddleware,
    monitor_auth_event,
    monitor_system_health,
    create_monitoring_blueprint,
    setup_monitoring,
    init_app
)


class TestRequestMonitoringMiddleware(unittest.TestCase):
    """Tests for the RequestMonitoringMiddleware class."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = Flask("test_app")
        self.middleware = RequestMonitoringMiddleware(self.app)
        self.client = self.app.test_client()
        
        # Add a test route
        @self.app.route("/test")
        def test_route():
            return "Test response"
        
        # Add a route that raises an exception
        @self.app.route("/error")
        def error_route():
            raise ValueError("Test error")
    
    @patch("api.v1.utils.monitoring.integration.record_request_metric")
    def test_request_monitoring(self, mock_record_metric):
        """Test that requests are monitored."""
        # Make a request
        response = self.client.get("/test")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Test response")
        
        # Check that metric was recorded
        mock_record_metric.assert_called_once()
        args, kwargs = mock_record_metric.call_args
        
        # Check arguments
        self.assertEqual(kwargs["endpoint"], "/test")
        self.assertEqual(kwargs["method"], "GET")
        self.assertEqual(kwargs["status_code"], 200)
        self.assertIsInstance(kwargs["response_time"], float)
    
    @patch("api.v1.utils.monitoring.integration.record_error_metric")
    def test_error_monitoring(self, mock_record_error):
        """Test that errors are monitored."""
        # Make a request that raises an exception
        with self.assertRaises(ValueError):
            with self.app.test_request_context("/error"):
                # Simulate before_request
                g.start_time = time.time()
                
                # Simulate exception in view
                error = ValueError("Test error")
                
                # Simulate teardown_request
                self.middleware.teardown_request(error)
        
        # Check that error metric was recorded
        mock_record_error.assert_called_once()
        args, kwargs = mock_record_error.call_args
        
        # Check arguments
        self.assertEqual(kwargs["endpoint"], "/error")
        self.assertEqual(kwargs["error_type"], "ValueError")
        self.assertEqual(kwargs["message"], "Test error")


class TestMonitoringFunctions(unittest.TestCase):
    """Tests for the monitoring utility functions."""
    
    @patch("api.v1.utils.monitoring.integration.record_auth_metric")
    @patch("api.v1.utils.monitoring.integration.send_alert")
    def test_monitor_auth_event(self, mock_send_alert, mock_record_auth):
        """Test monitoring of authentication events."""
        # Monitor successful login
        monitor_auth_event(
            auth_type="login",
            success=True,
            user_id="user123",
            client_ip="127.0.0.1",
            tags={"source": "web"}
        )
        
        # Check that auth metric was recorded
        mock_record_auth.assert_called_once()
        args, kwargs = mock_record_auth.call_args
        
        # Check arguments
        self.assertEqual(kwargs["name"], "auth_login")
        self.assertEqual(kwargs["auth_type"], "login")
        self.assertTrue(kwargs["success"])
        self.assertEqual(kwargs["user_id"], "user123")
        self.assertEqual(kwargs["client_ip"], "127.0.0.1")
        self.assertEqual(kwargs["tags"], {"source": "web"})
        
        # Alert should not be sent for successful auth
        mock_send_alert.assert_not_called()
        
        # Reset mocks
        mock_record_auth.reset_mock()
        mock_send_alert.reset_mock()
        
        # Monitor failed login
        monitor_auth_event(
            auth_type="login",
            success=False,
            user_id="user123",
            client_ip="127.0.0.1"
        )
        
        # Check that auth metric was recorded
        mock_record_auth.assert_called_once()
        
        # Check that alert was sent
        mock_send_alert.assert_called_once()
        args, kwargs = mock_send_alert.call_args
        
        # Check arguments
        self.assertEqual(kwargs["alert_type"], "security")
        self.assertEqual(kwargs["name"], "Failed Authentication")
        self.assertIn("failed login", kwargs["description"].lower())
        self.assertEqual(kwargs["severity"], "warning")
    
    @patch("api.v1.utils.monitoring.integration.record_system_metric")
    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("psutil.net_io_counters")
    def test_monitor_system_health(
        self, mock_net_io, mock_disk, mock_memory, mock_cpu, mock_record_metric
    ):
        """Test monitoring of system health."""
        # Mock system metrics
        mock_cpu.return_value = 45.2
        mock_memory.return_value = MagicMock(percent=60.5)
        mock_disk.return_value = MagicMock(percent=75.8)
        mock_net_io.return_value = MagicMock(
            bytes_sent=1024*1024, bytes_recv=2*1024*1024
        )
        
        # Create Flask app
        app = Flask("test_app")
        
        # Monitor system health
        monitor_system_health(app)
        
        # Check that system metrics were recorded
        expected_calls = [
            call(name="cpu_usage", value=45.2, component="system", host=unittest.mock.ANY),
            call(name="memory_usage", value=60.5, component="system", host=unittest.mock.ANY),
            call(name="disk_usage", value=75.8, component="system", host=unittest.mock.ANY),
            call(name="network_sent", value=1024*1024, component="system", host=unittest.mock.ANY),
            call(name="network_received", value=2*1024*1024, component="system", host=unittest.mock.ANY)
        ]
        
        # Check that all expected metrics were recorded
        mock_record_metric.assert_has_calls(expected_calls, any_order=True)


class TestMonitoringSetup(unittest.TestCase):
    """Tests for the monitoring setup functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = Flask("test_app")
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    @patch("api.v1.utils.monitoring.integration.initialize_metrics")
    @patch("api.v1.utils.monitoring.integration.initialize_alerts")
    @patch("api.v1.utils.monitoring.integration.initialize_dashboards")
    @patch("api.v1.utils.monitoring.integration._add_default_alert_rules")
    @patch("threading.Thread")
    def test_setup_monitoring(
        self, mock_thread, mock_add_rules, mock_init_dashboards, 
        mock_init_alerts, mock_init_metrics
    ):
        """Test setting up the monitoring system."""
        # Setup monitoring
        setup_monitoring(
            self.app, 
            storage_path=self.temp_dir,
            check_interval=30,
            enable_system_monitoring=True,
            system_monitoring_interval=60
        )
        
        # Check that components were initialized
        mock_init_metrics.assert_called_once_with(storage_path=self.temp_dir)
        mock_init_alerts.assert_called_once_with(
            storage_path=self.temp_dir, check_interval=30
        )
        mock_init_dashboards.assert_called_once_with(storage_path=self.temp_dir)
        
        # Check that default alert rules were added
        mock_add_rules.assert_called_once()
        
        # Check that system monitoring thread was started
        mock_thread.assert_called()
        thread_instance = mock_thread.return_value
        thread_instance.daemon = True
        thread_instance.start.assert_called_once()
    
    @patch("api.v1.utils.monitoring.integration.setup_monitoring")
    @patch("api.v1.utils.monitoring.integration.RequestMonitoringMiddleware")
    @patch("api.v1.utils.monitoring.integration.create_monitoring_blueprint")
    def test_init_app(
        self, mock_create_blueprint, mock_middleware, mock_setup
    ):
        """Test initializing monitoring for a Flask app."""
        # Mock blueprint
        mock_blueprint = MagicMock()
        mock_create_blueprint.return_value = mock_blueprint
        
        # Initialize monitoring
        init_app(self.app)
        
        # Check that setup_monitoring was called
        mock_setup.assert_called_once_with(self.app)
        
        # Check that RequestMonitoringMiddleware was initialized
        mock_middleware.assert_called_once_with(self.app)
        
        # Check that blueprint was registered
        self.app.register_blueprint.assert_called_once_with(mock_blueprint)
    
    def test_create_monitoring_blueprint(self):
        """Test creating a monitoring blueprint."""
        # Create blueprint
        blueprint = create_monitoring_blueprint()
        
        # Check blueprint properties
        self.assertEqual(blueprint.name, "monitoring")
        self.assertEqual(blueprint.url_prefix, "/api/monitoring")
        
        # Check that routes were registered
        routes = [rule.rule for rule in blueprint.url_map.iter_rules()]
        self.assertIn("/api/monitoring/metrics", routes)
        self.assertIn("/api/monitoring/alerts", routes)
        self.assertIn("/api/monitoring/dashboards", routes)
        self.assertIn("/api/monitoring/health", routes)


if __name__ == "__main__":
    unittest.main()
