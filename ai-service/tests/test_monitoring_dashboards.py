"""
Tests for the Monitoring Dashboards System

This module contains tests for the dashboard components and data retrieval
functionality of the TechSaaS monitoring system.
"""

import unittest
import time
import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

from api.v1.utils.monitoring.dashboards import (
    DashboardManager,
    initialize_dashboards,
    register_dashboard_provider,
    add_dashboard_config,
    get_dashboard_config,
    get_dashboard_configs,
    get_dashboard_data,
    delete_dashboard_config,
    DEFAULT_DASHBOARDS
)
from api.v1.utils.monitoring.metrics import TIME_WINDOW_5MIN


class TestDashboardManager(unittest.TestCase):
    """Tests for the DashboardManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.dashboard_manager = DashboardManager()
        self.dashboard_manager.initialize(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_dashboard_config(self):
        """Test adding a dashboard configuration."""
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"],
            "window": TIME_WINDOW_5MIN
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Check if config was added
        stored_config = self.dashboard_manager.get_dashboard_config("test_dashboard")
        self.assertIsNotNone(stored_config)
        self.assertEqual(stored_config["name"], "Test Dashboard")
        self.assertEqual(stored_config["type"], "metrics")
        self.assertEqual(stored_config["metrics"], ["cpu_usage", "memory_usage"])
    
    def test_get_dashboard_configs(self):
        """Test getting all dashboard configurations."""
        # Add multiple configs
        config1 = {
            "id": "dashboard1",
            "name": "Dashboard 1",
            "description": "First dashboard",
            "type": "metrics",
            "metrics": ["cpu_usage"]
        }
        
        config2 = {
            "id": "dashboard2",
            "name": "Dashboard 2",
            "description": "Second dashboard",
            "type": "alerts",
            "severity": ["warning", "error"]
        }
        
        self.dashboard_manager.add_dashboard_config("dashboard1", config1)
        self.dashboard_manager.add_dashboard_config("dashboard2", config2)
        
        # Get all configs
        configs = self.dashboard_manager.get_dashboard_configs()
        
        # Check results
        self.assertEqual(len(configs), 2)
        self.assertIn("dashboard1", configs)
        self.assertIn("dashboard2", configs)
        self.assertEqual(configs["dashboard1"]["name"], "Dashboard 1")
        self.assertEqual(configs["dashboard2"]["name"], "Dashboard 2")
    
    def test_delete_dashboard_config(self):
        """Test deleting a dashboard configuration."""
        # Add a config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"]
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Delete the config
        result = self.dashboard_manager.delete_dashboard_config("test_dashboard")
        
        # Check if config was deleted
        self.assertTrue(result)
        self.assertIsNone(self.dashboard_manager.get_dashboard_config("test_dashboard"))
    
    @patch("api.v1.utils.monitoring.metrics.get_metric_summary")
    def test_get_metrics_dashboard_data(self, mock_get_summary):
        """Test getting data for a metrics dashboard."""
        # Mock the metrics summary
        mock_get_summary.return_value = {
            "cpu_usage": {
                "avg": 45.0,
                "max": 80.0,
                "min": 10.0,
                "count": 10
            },
            "memory_usage": {
                "avg": 60.0,
                "max": 75.0,
                "min": 45.0,
                "count": 10
            }
        }
        
        # Add a metrics dashboard config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"],
            "window": TIME_WINDOW_5MIN
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Get dashboard data
        data = self.dashboard_manager.get_dashboard_data("test_dashboard")
        
        # Check results
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(data["type"], "metrics")
        self.assertIn("metrics", data)
        self.assertEqual(len(data["metrics"]), 2)
        
        metrics = data["metrics"]
        self.assertIn("cpu_usage", [m["name"] for m in metrics])
        self.assertIn("memory_usage", [m["name"] for m in metrics])
        
        for metric in metrics:
            if metric["name"] == "cpu_usage":
                self.assertEqual(metric["avg"], 45.0)
                self.assertEqual(metric["max"], 80.0)
                self.assertEqual(metric["min"], 10.0)
            elif metric["name"] == "memory_usage":
                self.assertEqual(metric["avg"], 60.0)
                self.assertEqual(metric["max"], 75.0)
                self.assertEqual(metric["min"], 45.0)
    
    @patch("api.v1.utils.monitoring.alerts.get_alerts")
    @patch("api.v1.utils.monitoring.alerts.get_alert_rules")
    def test_get_alerts_dashboard_data(self, mock_get_rules, mock_get_alerts):
        """Test getting data for an alerts dashboard."""
        # Mock alert rules
        mock_get_rules.return_value = [
            {
                "id": "rule1",
                "name": "High CPU Usage",
                "description": "Alert when CPU usage is too high",
                "metric_type": "system",
                "metric_name": "cpu_usage",
                "condition": "gt",
                "threshold": 80.0,
                "severity": "warning",
                "enabled": True
            },
            {
                "id": "rule2",
                "name": "High Memory Usage",
                "description": "Alert when memory usage is too high",
                "metric_type": "system",
                "metric_name": "memory_usage",
                "condition": "gt",
                "threshold": 90.0,
                "severity": "error",
                "enabled": True
            }
        ]
        
        # Mock alerts
        mock_get_alerts.return_value = [
            {
                "id": "alert1",
                "rule_id": "rule1",
                "name": "High CPU Usage",
                "description": "CPU usage above threshold",
                "metric_type": "system",
                "metric_name": "cpu_usage",
                "condition": "gt",
                "threshold": 80.0,
                "actual_value": 85.0,
                "severity": "warning",
                "status": "active",
                "created_at": time.time() - 3600,
                "updated_at": time.time() - 1800
            },
            {
                "id": "alert2",
                "rule_id": "rule2",
                "name": "High Memory Usage",
                "description": "Memory usage above threshold",
                "metric_type": "system",
                "metric_name": "memory_usage",
                "condition": "gt",
                "threshold": 90.0,
                "actual_value": 95.0,
                "severity": "error",
                "status": "active",
                "created_at": time.time() - 1800,
                "updated_at": time.time() - 900
            }
        ]
        
        # Add an alerts dashboard config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "alerts",
            "severity": ["warning", "error"],
            "status": ["active"]
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Get dashboard data
        data = self.dashboard_manager.get_dashboard_data("test_dashboard")
        
        # Check results
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(data["type"], "alerts")
        self.assertIn("alerts", data)
        self.assertEqual(len(data["alerts"]), 2)
        self.assertIn("rules", data)
        self.assertEqual(len(data["rules"]), 2)
        self.assertIn("statistics", data)
        
        statistics = data["statistics"]
        self.assertEqual(statistics["total"], 2)
        self.assertEqual(statistics["active"], 2)
        self.assertEqual(statistics["by_severity"]["warning"], 1)
        self.assertEqual(statistics["by_severity"]["error"], 1)
    
    @patch("api.v1.utils.monitoring.metrics.get_metric_summary")
    def test_get_system_dashboard_data(self, mock_get_summary):
        """Test getting data for a system dashboard."""
        # Mock the metrics summary
        mock_get_summary.return_value = {
            "cpu_usage": {
                "avg": 45.0,
                "max": 80.0,
                "min": 10.0,
                "count": 10
            },
            "memory_usage": {
                "avg": 60.0,
                "max": 75.0,
                "min": 45.0,
                "count": 10
            },
            "disk_usage": {
                "avg": 70.0,
                "max": 75.0,
                "min": 65.0,
                "count": 10
            },
            "network_in": {
                "avg": 1024.0,
                "max": 2048.0,
                "min": 512.0,
                "count": 10
            },
            "network_out": {
                "avg": 512.0,
                "max": 1024.0,
                "min": 256.0,
                "count": 10
            }
        }
        
        # Add a system dashboard config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "system",
            "resources": ["cpu", "memory", "disk", "network"]
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Get dashboard data
        data = self.dashboard_manager.get_dashboard_data("test_dashboard")
        
        # Check results
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(data["type"], "system")
        self.assertIn("resources", data)
        
        resources = data["resources"]
        self.assertEqual(len(resources), 4)
        
        resource_names = [r["name"] for r in resources]
        self.assertIn("cpu", resource_names)
        self.assertIn("memory", resource_names)
        self.assertIn("disk", resource_names)
        self.assertIn("network", resource_names)
        
        for resource in resources:
            if resource["name"] == "cpu":
                self.assertEqual(resource["usage"], 45.0)
                self.assertEqual(resource["max"], 80.0)
            elif resource["name"] == "memory":
                self.assertEqual(resource["usage"], 60.0)
                self.assertEqual(resource["max"], 75.0)
            elif resource["name"] == "disk":
                self.assertEqual(resource["usage"], 70.0)
                self.assertEqual(resource["max"], 75.0)
            elif resource["name"] == "network":
                self.assertIn("in", resource)
                self.assertIn("out", resource)
                self.assertEqual(resource["in"]["avg"], 1024.0)
                self.assertEqual(resource["out"]["avg"], 512.0)
    
    def test_register_dashboard_provider(self):
        """Test registering a custom dashboard provider."""
        # Define a custom provider
        def custom_provider(config):
            return {
                "name": config["name"],
                "type": "custom",
                "data": {"value": 42}
            }
        
        # Register the provider
        self.dashboard_manager.register_dashboard_provider("custom", custom_provider)
        
        # Add a custom dashboard config
        config = {
            "id": "custom_dashboard",
            "name": "Custom Dashboard",
            "description": "Dashboard with custom provider",
            "type": "custom"
        }
        
        self.dashboard_manager.add_dashboard_config("custom_dashboard", config)
        
        # Get dashboard data
        data = self.dashboard_manager.get_dashboard_data("custom_dashboard")
        
        # Check results
        self.assertEqual(data["name"], "Custom Dashboard")
        self.assertEqual(data["type"], "custom")
        self.assertIn("data", data)
        self.assertEqual(data["data"]["value"], 42)
    
    def test_save_and_load_config(self):
        """Test saving and loading dashboard configurations."""
        # Add a dashboard config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"]
        }
        
        self.dashboard_manager.add_dashboard_config("test_dashboard", config)
        
        # Save configs
        self.dashboard_manager._save_dashboard_configs()
        
        # Create a new manager and load configs
        new_manager = DashboardManager()
        new_manager.initialize(storage_path=self.temp_dir)
        
        # Check if configs were loaded
        stored_config = new_manager.get_dashboard_config("test_dashboard")
        self.assertIsNotNone(stored_config)
        self.assertEqual(stored_config["name"], "Test Dashboard")
        self.assertEqual(stored_config["type"], "metrics")
        self.assertEqual(stored_config["metrics"], ["cpu_usage", "memory_usage"])


class TestPublicAPI(unittest.TestCase):
    """Tests for the public API functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        initialize_dashboards(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_dashboard_config(self):
        """Test adding a dashboard configuration."""
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"]
        }
        
        add_dashboard_config("test_dashboard", config)
        
        # Check if config was added
        stored_config = get_dashboard_config("test_dashboard")
        self.assertIsNotNone(stored_config)
        self.assertEqual(stored_config["name"], "Test Dashboard")
        self.assertEqual(stored_config["type"], "metrics")
        self.assertEqual(stored_config["metrics"], ["cpu_usage", "memory_usage"])
    
    def test_get_dashboard_configs(self):
        """Test getting all dashboard configurations."""
        # Add multiple configs
        config1 = {
            "id": "dashboard1",
            "name": "Dashboard 1",
            "description": "First dashboard",
            "type": "metrics",
            "metrics": ["cpu_usage"]
        }
        
        config2 = {
            "id": "dashboard2",
            "name": "Dashboard 2",
            "description": "Second dashboard",
            "type": "alerts",
            "severity": ["warning", "error"]
        }
        
        add_dashboard_config("dashboard1", config1)
        add_dashboard_config("dashboard2", config2)
        
        # Get all configs
        configs = get_dashboard_configs()
        
        # Check results
        self.assertEqual(len(configs), 2)
        self.assertIn("dashboard1", configs)
        self.assertIn("dashboard2", configs)
        self.assertEqual(configs["dashboard1"]["name"], "Dashboard 1")
        self.assertEqual(configs["dashboard2"]["name"], "Dashboard 2")
    
    def test_delete_dashboard_config(self):
        """Test deleting a dashboard configuration."""
        # Add a config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"]
        }
        
        add_dashboard_config("test_dashboard", config)
        
        # Delete the config
        result = delete_dashboard_config("test_dashboard")
        
        # Check if config was deleted
        self.assertTrue(result)
        self.assertIsNone(get_dashboard_config("test_dashboard"))
    
    @patch("api.v1.utils.monitoring.metrics.get_metric_summary")
    def test_get_dashboard_data(self, mock_get_summary):
        """Test getting dashboard data."""
        # Mock the metrics summary
        mock_get_summary.return_value = {
            "cpu_usage": {
                "avg": 45.0,
                "max": 80.0,
                "min": 10.0,
                "count": 10
            },
            "memory_usage": {
                "avg": 60.0,
                "max": 75.0,
                "min": 45.0,
                "count": 10
            }
        }
        
        # Add a dashboard config
        config = {
            "id": "test_dashboard",
            "name": "Test Dashboard",
            "description": "Dashboard for testing",
            "type": "metrics",
            "metrics": ["cpu_usage", "memory_usage"]
        }
        
        add_dashboard_config("test_dashboard", config)
        
        # Get dashboard data
        data = get_dashboard_data("test_dashboard")
        
        # Check results
        self.assertEqual(data["name"], "Test Dashboard")
        self.assertEqual(data["type"], "metrics")
        self.assertIn("metrics", data)
        self.assertEqual(len(data["metrics"]), 2)
    
    def test_default_dashboards(self):
        """Test that default dashboards are available."""
        # Check that DEFAULT_DASHBOARDS is defined and not empty
        self.assertIsNotNone(DEFAULT_DASHBOARDS)
        self.assertTrue(len(DEFAULT_DASHBOARDS) > 0)
        
        # Check structure of default dashboards
        for dashboard_id, config in DEFAULT_DASHBOARDS.items():
            self.assertIn("id", config)
            self.assertIn("name", config)
            self.assertIn("type", config)
            self.assertEqual(config["id"], dashboard_id)


if __name__ == "__main__":
    unittest.main()
