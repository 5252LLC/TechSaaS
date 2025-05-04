"""
Dashboards for TechSaaS Monitoring

This module provides dashboard capabilities for visualizing metrics and alerts,
enabling administrators to monitor system health and performance.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import threading

from api.v1.utils.logging import get_logger
from api.v1.utils.monitoring.metrics import (
    get_metric_summary,
    get_metrics,
    TIME_WINDOW_5MIN,
    TIME_WINDOW_1HOUR, 
    TIME_WINDOW_1DAY
)
from api.v1.utils.monitoring.alerts import (
    get_alerts,
    get_alert_rules
)

# Get logger for this module
logger = get_logger(__name__)

# Dashboard types
DASHBOARD_TYPE_METRICS = "metrics"
DASHBOARD_TYPE_ALERTS = "alerts"
DASHBOARD_TYPE_SYSTEM = "system"
DASHBOARD_TYPE_CUSTOM = "custom"

class DashboardManager:
    """Manager for dashboard components and data."""
    
    def __init__(self):
        """Initialize dashboard manager."""
        self._dashboard_configs = {}  # id -> config
        self._dashboard_providers = {}  # type -> provider function
        self._storage_path = None
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize(self, storage_path: Optional[str] = None) -> None:
        """
        Initialize the dashboard manager.
        
        Args:
            storage_path: Directory to store dashboard configurations
        """
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
            
            # Load existing dashboard configs
            self._load_dashboard_configs()
        
        # Register built-in dashboard providers
        self._register_default_providers()
        
        self._initialized = True
        logger.info(f"Dashboard manager initialized with storage_path={storage_path}")
    
    def _register_default_providers(self) -> None:
        """Register built-in dashboard data providers."""
        self._dashboard_providers[DASHBOARD_TYPE_METRICS] = self._get_metrics_dashboard_data
        self._dashboard_providers[DASHBOARD_TYPE_ALERTS] = self._get_alerts_dashboard_data
        self._dashboard_providers[DASHBOARD_TYPE_SYSTEM] = self._get_system_dashboard_data
    
    def register_dashboard_provider(self, dashboard_type: str, 
                                  provider: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Register a custom dashboard data provider.
        
        Args:
            dashboard_type: Type of dashboard
            provider: Function to provide dashboard data
        """
        self._dashboard_providers[dashboard_type] = provider
        logger.info(f"Registered dashboard provider for type: {dashboard_type}")
    
    def add_dashboard_config(self, dashboard_id: str, config: Dict[str, Any]) -> None:
        """
        Add or update a dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            config: Dashboard configuration
        """
        with self._lock:
            self._dashboard_configs[dashboard_id] = config
            
            # Persist configs
            if self._storage_path:
                self._save_dashboard_configs()
    
    def get_dashboard_config(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard configuration or None if not found
        """
        with self._lock:
            return self._dashboard_configs.get(dashboard_id)
    
    def get_dashboard_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all dashboard configurations.
        
        Returns:
            Dictionary of dashboard configurations
        """
        with self._lock:
            return self._dashboard_configs.copy()
    
    def delete_dashboard_config(self, dashboard_id: str) -> bool:
        """
        Delete a dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if dashboard_id not in self._dashboard_configs:
                return False
            
            del self._dashboard_configs[dashboard_id]
            
            # Persist configs
            if self._storage_path:
                self._save_dashboard_configs()
            
            return True
    
    def get_dashboard_data(self, dashboard_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get data for a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            params: Additional parameters
            
        Returns:
            Dashboard data
        """
        # Get dashboard config
        config = self.get_dashboard_config(dashboard_id)
        if not config:
            logger.warning(f"Dashboard config not found: {dashboard_id}")
            return {"error": "Dashboard not found"}
        
        # Get dashboard type
        dashboard_type = config.get("type", DASHBOARD_TYPE_METRICS)
        
        # Check if provider exists
        if dashboard_type not in self._dashboard_providers:
            logger.warning(f"Dashboard provider not found for type: {dashboard_type}")
            return {"error": f"Dashboard provider not found for type: {dashboard_type}"}
        
        # Merge params with config
        if params:
            merged_config = {**config, **params}
        else:
            merged_config = config.copy()
        
        # Call provider
        try:
            data = self._dashboard_providers[dashboard_type](merged_config)
            return data
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}", exc_info=True)
            return {"error": f"Error getting dashboard data: {str(e)}"}
    
    def _get_metrics_dashboard_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data for a metrics dashboard.
        
        Args:
            config: Dashboard configuration
            
        Returns:
            Dashboard data
        """
        # Get metric type
        metric_type = config.get("metric_type")
        
        # Get time windows
        time_windows = config.get("time_windows", [
            TIME_WINDOW_5MIN,
            TIME_WINDOW_1HOUR,
            TIME_WINDOW_1DAY
        ])
        
        # Get metrics for each window
        metrics_data = {}
        for window in time_windows:
            metrics = get_metric_summary(metric_type, window)
            metrics_data[f"{window}s"] = metrics
        
        # Get recent metric entries if requested
        recent_limit = config.get("recent_limit", 0)
        recent_metrics = []
        
        if recent_limit > 0:
            filters = {}
            if metric_type:
                filters["metric_type"] = metric_type
            
            recent_metrics = get_metrics(
                metric_type=metric_type,
                limit=recent_limit,
                filters=config.get("filters")
            )
        
        return {
            "dashboard_id": config.get("id", "unknown"),
            "title": config.get("title", "Metrics Dashboard"),
            "metric_type": metric_type,
            "time_windows": time_windows,
            "metrics": metrics_data,
            "recent_metrics": recent_metrics,
            "timestamp": datetime.now().timestamp()
        }
    
    def _get_alerts_dashboard_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data for an alerts dashboard.
        
        Args:
            config: Dashboard configuration
            
        Returns:
            Dashboard data
        """
        # Get alert filters
        status = config.get("status")
        severity = config.get("severity")
        rule_id = config.get("rule_id")
        
        # Get time range
        start_time = config.get("start_time")
        end_time = config.get("end_time")
        
        # Get limit
        limit = config.get("limit", 100)
        
        # Get alerts
        alerts = get_alerts(status, severity, rule_id, start_time, end_time, limit)
        
        # Get alert rules if requested
        include_rules = config.get("include_rules", False)
        rules = []
        
        if include_rules:
            rules = get_alert_rules(config.get("enabled_only", False))
        
        # Get alert statistics
        alert_stats = self._get_alert_statistics(alerts)
        
        return {
            "dashboard_id": config.get("id", "unknown"),
            "title": config.get("title", "Alerts Dashboard"),
            "alerts": alerts,
            "rules": rules,
            "stats": alert_stats,
            "timestamp": datetime.now().timestamp()
        }
    
    def _get_system_dashboard_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data for a system dashboard.
        
        Args:
            config: Dashboard configuration
            
        Returns:
            Dashboard data
        """
        # Get system metrics
        metrics = get_metric_summary("system", config.get("window", TIME_WINDOW_5MIN))
        
        # Get recent system errors
        error_limit = config.get("error_limit", 10)
        errors = get_metrics(
            metric_type="error",
            limit=error_limit,
            filters={"type": "system"}
        )
        
        # Get system alerts
        alerts = get_alerts(
            severity=config.get("alert_severity"),
            rule_id=config.get("alert_rule_id"),
            limit=config.get("alert_limit", 10)
        )
        
        return {
            "dashboard_id": config.get("id", "unknown"),
            "title": config.get("title", "System Dashboard"),
            "metrics": metrics,
            "errors": errors,
            "alerts": alerts,
            "timestamp": datetime.now().timestamp()
        }
    
    def _get_alert_statistics(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics for alerts.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Alert statistics
        """
        # Count by severity
        severity_counts = {}
        for alert in alerts:
            severity = alert.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by status
        status_counts = {}
        for alert in alerts:
            status = alert.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by time period
        now = datetime.now().timestamp()
        last_hour = now - 3600
        last_day = now - 86400
        
        alerts_last_hour = sum(1 for a in alerts if a.get("created_at", 0) >= last_hour)
        alerts_last_day = sum(1 for a in alerts if a.get("created_at", 0) >= last_day)
        
        return {
            "total": len(alerts),
            "by_severity": severity_counts,
            "by_status": status_counts,
            "last_hour": alerts_last_hour,
            "last_day": alerts_last_day
        }
    
    def _save_dashboard_configs(self) -> None:
        """Save dashboard configurations to disk."""
        if not self._storage_path:
            return
        
        try:
            # Create configs file
            filename = os.path.join(self._storage_path, "dashboard_configs.json")
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(self._dashboard_configs, f, indent=2)
                
            logger.info(f"Saved {len(self._dashboard_configs)} dashboard configs to {filename}")
        except Exception as e:
            logger.error(f"Error saving dashboard configs: {e}", exc_info=True)
    
    def _load_dashboard_configs(self) -> None:
        """Load dashboard configurations from disk."""
        if not self._storage_path:
            return
        
        filename = os.path.join(self._storage_path, "dashboard_configs.json")
        
        if not os.path.exists(filename):
            return
        
        try:
            # Read file
            with open(filename, 'r') as f:
                self._dashboard_configs = json.load(f)
                
            logger.info(f"Loaded {len(self._dashboard_configs)} dashboard configs from {filename}")
        except Exception as e:
            logger.error(f"Error loading dashboard configs: {e}", exc_info=True)

# Global instance
_dashboard_manager = DashboardManager()

def initialize_dashboards(storage_path: Optional[str] = None) -> None:
    """
    Initialize the dashboards system.
    
    Args:
        storage_path: Directory to store dashboard configurations
    """
    _dashboard_manager.initialize(storage_path)

def register_dashboard_provider(dashboard_type: str, 
                              provider: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
    """
    Register a custom dashboard data provider.
    
    Args:
        dashboard_type: Type of dashboard
        provider: Function to provide dashboard data
    """
    _dashboard_manager.register_dashboard_provider(dashboard_type, provider)

def add_dashboard_config(dashboard_id: str, config: Dict[str, Any]) -> None:
    """
    Add or update a dashboard configuration.
    
    Args:
        dashboard_id: Dashboard ID
        config: Dashboard configuration
    """
    _dashboard_manager.add_dashboard_config(dashboard_id, config)

def get_dashboard_config(dashboard_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a dashboard configuration.
    
    Args:
        dashboard_id: Dashboard ID
        
    Returns:
        Dashboard configuration or None if not found
    """
    return _dashboard_manager.get_dashboard_config(dashboard_id)

def get_dashboard_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get all dashboard configurations.
    
    Returns:
        Dictionary of dashboard configurations
    """
    return _dashboard_manager.get_dashboard_configs()

def get_dashboard_data(dashboard_id: str, 
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get data for a dashboard.
    
    Args:
        dashboard_id: Dashboard ID
        params: Additional parameters
        
    Returns:
        Dashboard data
    """
    return _dashboard_manager.get_dashboard_data(dashboard_id, params)

def delete_dashboard_config(dashboard_id: str) -> bool:
    """
    Delete a dashboard configuration.
    
    Args:
        dashboard_id: Dashboard ID
        
    Returns:
        True if deleted, False if not found
    """
    return _dashboard_manager.delete_dashboard_config(dashboard_id)

# Default dashboard configurations
DEFAULT_DASHBOARDS = {
    "api_performance": {
        "id": "api_performance",
        "type": DASHBOARD_TYPE_METRICS,
        "title": "API Performance Dashboard",
        "description": "Monitor API response times and error rates",
        "metric_type": "request",
        "time_windows": [TIME_WINDOW_5MIN, TIME_WINDOW_1HOUR, TIME_WINDOW_1DAY],
        "recent_limit": 20
    },
    "error_monitoring": {
        "id": "error_monitoring",
        "type": DASHBOARD_TYPE_METRICS,
        "title": "Error Monitoring Dashboard",
        "description": "Track application errors and exceptions",
        "metric_type": "error",
        "time_windows": [TIME_WINDOW_5MIN, TIME_WINDOW_1HOUR, TIME_WINDOW_1DAY],
        "recent_limit": 50
    },
    "active_alerts": {
        "id": "active_alerts",
        "type": DASHBOARD_TYPE_ALERTS,
        "title": "Active Alerts Dashboard",
        "description": "View and manage active alerts",
        "status": "active",
        "include_rules": True,
        "limit": 100
    },
    "system_health": {
        "id": "system_health",
        "type": DASHBOARD_TYPE_SYSTEM,
        "title": "System Health Dashboard",
        "description": "Monitor overall system health and performance",
        "window": TIME_WINDOW_5MIN,
        "error_limit": 10,
        "alert_limit": 10
    }
}
