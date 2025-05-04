"""
Tests for the Monitoring Metrics System

This module contains tests for the metrics collection, storage, and retrieval
functionality of the TechSaaS monitoring system.
"""

import unittest
import time
import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Update imports to use the correct package structure
from api.v1.utils.monitoring.metrics import (
    Metric,
    RequestMetric,
    ErrorMetric,
    AuthMetric,
    SystemMetric,
    MetricsManager,
    initialize_metrics,
    record_request_metric,
    record_error_metric,
    record_auth_metric,
    record_system_metric,
    get_metric_summary,
    get_metrics,
    TIME_WINDOW_5MIN
)


class TestMetricClasses(unittest.TestCase):
    """Tests for the metric data classes."""
    
    def test_base_metric(self):
        """Test the base Metric class."""
        metric = Metric(type="test", name="test_metric", value=42.0)
        self.assertEqual(metric.type, "test")
        self.assertEqual(metric.name, "test_metric")
        self.assertEqual(metric.value, 42.0)
        self.assertIsNotNone(metric.timestamp)
        self.assertEqual(metric.tags, {})
        
        # Test conversion to dict
        metric_dict = metric.to_dict()
        self.assertEqual(metric_dict["type"], "test")
        self.assertEqual(metric_dict["name"], "test_metric")
        self.assertEqual(metric_dict["value"], 42.0)
        self.assertIsNotNone(metric_dict["timestamp"])
        self.assertEqual(metric_dict["tags"], {})
        
        # Test from_dict
        new_metric = Metric.from_dict(metric_dict)
        self.assertEqual(new_metric.type, metric.type)
        self.assertEqual(new_metric.name, metric.name)
        self.assertEqual(new_metric.value, metric.value)
        self.assertEqual(new_metric.timestamp, metric.timestamp)
        self.assertEqual(new_metric.tags, metric.tags)
    
    def test_request_metric(self):
        """Test the RequestMetric class."""
        metric = RequestMetric(
            name="api_request",
            value=0.125,
            endpoint="/api/v1/users",
            method="GET",
            status_code=200,
            response_time=125.0,
            client_ip="127.0.0.1",
            user_id="user123"
        )
        self.assertEqual(metric.type, "request")
        self.assertEqual(metric.name, "api_request")
        self.assertEqual(metric.value, 0.125)
        self.assertEqual(metric.endpoint, "/api/v1/users")
        self.assertEqual(metric.method, "GET")
        self.assertEqual(metric.status_code, 200)
        self.assertEqual(metric.response_time, 125.0)
        self.assertEqual(metric.client_ip, "127.0.0.1")
        self.assertEqual(metric.user_id, "user123")
    
    def test_error_metric(self):
        """Test the ErrorMetric class."""
        metric = ErrorMetric(
            name="api_error",
            value=1,
            error_type="ValidationError",
            message="Invalid input",
            endpoint="/api/v1/users",
            method="POST",
            client_ip="127.0.0.1",
            user_id="user123"
        )
        self.assertEqual(metric.type, "error")
        self.assertEqual(metric.name, "api_error")
        self.assertEqual(metric.value, 1)
        self.assertEqual(metric.error_type, "ValidationError")
        self.assertEqual(metric.message, "Invalid input")
        self.assertEqual(metric.endpoint, "/api/v1/users")
        self.assertEqual(metric.method, "POST")
        self.assertEqual(metric.client_ip, "127.0.0.1")
        self.assertEqual(metric.user_id, "user123")
    
    def test_auth_metric(self):
        """Test the AuthMetric class."""
        metric = AuthMetric(
            name="login_attempt",
            value=1,
            auth_type="password",
            success=True,
            user_id="user123",
            client_ip="127.0.0.1"
        )
        self.assertEqual(metric.type, "auth")
        self.assertEqual(metric.name, "login_attempt")
        self.assertEqual(metric.value, 1)
        self.assertEqual(metric.auth_type, "password")
        self.assertTrue(metric.success)
        self.assertEqual(metric.user_id, "user123")
        self.assertEqual(metric.client_ip, "127.0.0.1")
    
    def test_system_metric(self):
        """Test the SystemMetric class."""
        metric = SystemMetric(
            name="cpu_usage",
            value=45.2,
            component="api_server",
            host="web-1"
        )
        self.assertEqual(metric.type, "system")
        self.assertEqual(metric.name, "cpu_usage")
        self.assertEqual(metric.value, 45.2)
        self.assertEqual(metric.component, "api_server")
        self.assertEqual(metric.host, "web-1")


class TestMetricsManager(unittest.TestCase):
    """Tests for the MetricsManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_manager = MetricsManager()
        self.metrics_manager.initialize(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_metric(self):
        """Test adding a metric."""
        metric = Metric(type="test", name="test_metric", value=42.0)
        self.metrics_manager.add_metric(metric)
        
        # Get metrics and check if added
        metrics = self.metrics_manager.get_metrics(metric_type="test")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "test_metric")
        self.assertEqual(metrics[0]["value"], 42.0)
    
    def test_get_metrics_filtering(self):
        """Test filtering metrics."""
        # Add multiple metrics
        self.metrics_manager.add_metric(Metric(type="test", name="metric1", value=1.0))
        self.metrics_manager.add_metric(Metric(type="test", name="metric2", value=2.0))
        self.metrics_manager.add_metric(Metric(type="other", name="metric3", value=3.0))
        
        # Test type filter
        metrics = self.metrics_manager.get_metrics(metric_type="test")
        self.assertEqual(len(metrics), 2)
        names = [m["name"] for m in metrics]
        self.assertIn("metric1", names)
        self.assertIn("metric2", names)
        
        # Test time filter
        future_time = time.time() + 3600
        metrics = self.metrics_manager.get_metrics(start_time=future_time)
        self.assertEqual(len(metrics), 0)
        
        # Test limit
        metrics = self.metrics_manager.get_metrics(limit=1)
        self.assertEqual(len(metrics), 1)
        
        # Test custom filter
        metrics = self.metrics_manager.get_metrics(filters={"name": "metric1"})
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "metric1")
    
    def test_aggregated_metrics(self):
        """Test metrics aggregation."""
        # Add metrics for aggregation
        for i in range(10):
            self.metrics_manager.add_metric(
                Metric(type="test", name="response_time", value=i * 10.0)
            )
        
        # Force aggregation
        self.metrics_manager._aggregate_metrics()
        
        # Get aggregated metrics
        agg_metrics = self.metrics_manager.get_aggregated_metrics(metric_type="test")
        
        # Check results
        self.assertIn("response_time", agg_metrics)
        self.assertIn("avg", agg_metrics["response_time"])
        self.assertIn("min", agg_metrics["response_time"])
        self.assertIn("max", agg_metrics["response_time"])
        self.assertIn("count", agg_metrics["response_time"])
        
        # Check values
        self.assertEqual(agg_metrics["response_time"]["count"], 10)
        self.assertEqual(agg_metrics["response_time"]["min"], 0.0)
        self.assertEqual(agg_metrics["response_time"]["max"], 90.0)
        self.assertEqual(agg_metrics["response_time"]["avg"], 45.0)
    
    def test_persist_and_load(self):
        """Test persisting and loading metrics."""
        # Add some metrics
        self.metrics_manager.add_metric(Metric(type="test", name="metric1", value=1.0))
        self.metrics_manager.add_metric(Metric(type="test", name="metric2", value=2.0))
        
        # Persist
        self.metrics_manager._persist_metrics()
        
        # Create new manager and load
        new_manager = MetricsManager()
        new_manager.initialize(storage_path=self.temp_dir)
        new_manager._load_metrics()
        
        # Check if metrics were loaded
        metrics = new_manager.get_metrics(metric_type="test")
        self.assertEqual(len(metrics), 2)
        names = [m["name"] for m in metrics]
        self.assertIn("metric1", names)
        self.assertIn("metric2", names)


class TestPublicAPI(unittest.TestCase):
    """Tests for the public API functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        initialize_metrics(storage_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
    
    def test_record_request_metric(self):
        """Test recording a request metric."""
        record_request_metric(
            name="api_request",
            endpoint="/api/v1/users",
            method="GET",
            status_code=200,
            response_time=125.0,
            client_ip="127.0.0.1",
            user_id="user123"
        )
        
        # Check if metric was recorded
        metrics = get_metrics(metric_type="request")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "api_request")
        self.assertEqual(metrics[0]["endpoint"], "/api/v1/users")
        self.assertEqual(metrics[0]["method"], "GET")
        self.assertEqual(metrics[0]["status_code"], 200)
        self.assertEqual(metrics[0]["response_time"], 125.0)
        self.assertEqual(metrics[0]["client_ip"], "127.0.0.1")
        self.assertEqual(metrics[0]["user_id"], "user123")
    
    def test_record_error_metric(self):
        """Test recording an error metric."""
        record_error_metric(
            name="api_error",
            error_type="ValidationError",
            message="Invalid input",
            endpoint="/api/v1/users",
            method="POST",
            client_ip="127.0.0.1",
            user_id="user123"
        )
        
        # Check if metric was recorded
        metrics = get_metrics(metric_type="error")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "api_error")
        self.assertEqual(metrics[0]["error_type"], "ValidationError")
        self.assertEqual(metrics[0]["message"], "Invalid input")
        self.assertEqual(metrics[0]["endpoint"], "/api/v1/users")
        self.assertEqual(metrics[0]["method"], "POST")
        self.assertEqual(metrics[0]["client_ip"], "127.0.0.1")
        self.assertEqual(metrics[0]["user_id"], "user123")
    
    def test_record_auth_metric(self):
        """Test recording an auth metric."""
        record_auth_metric(
            name="login_attempt",
            auth_type="password",
            success=True,
            user_id="user123",
            client_ip="127.0.0.1"
        )
        
        # Check if metric was recorded
        metrics = get_metrics(metric_type="auth")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "login_attempt")
        self.assertEqual(metrics[0]["auth_type"], "password")
        self.assertTrue(metrics[0]["success"])
        self.assertEqual(metrics[0]["user_id"], "user123")
        self.assertEqual(metrics[0]["client_ip"], "127.0.0.1")
    
    def test_record_system_metric(self):
        """Test recording a system metric."""
        record_system_metric(
            name="cpu_usage",
            value=45.2,
            component="api_server",
            host="web-1"
        )
        
        # Check if metric was recorded
        metrics = get_metrics(metric_type="system")
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]["name"], "cpu_usage")
        self.assertEqual(metrics[0]["value"], 45.2)
        self.assertEqual(metrics[0]["component"], "api_server")
        self.assertEqual(metrics[0]["host"], "web-1")
    
    def test_get_metric_summary(self):
        """Test getting a metric summary."""
        # Add multiple metrics with same name
        for i in range(5):
            record_system_metric(name="cpu_usage", value=i * 10.0)
        
        # Get summary
        summary = get_metric_summary(metric_type="system")
        
        # Check results
        self.assertIn("cpu_usage", summary)
        self.assertIn("avg", summary["cpu_usage"])
        self.assertIn("min", summary["cpu_usage"])
        self.assertIn("max", summary["cpu_usage"])
        self.assertIn("count", summary["cpu_usage"])


if __name__ == "__main__":
    unittest.main()
