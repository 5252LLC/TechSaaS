"""
Monitoring System for TechSaaS Platform

This module provides monitoring capabilities for the TechSaaS platform,
including metrics collection, alerting, and dashboards.
"""

from api.v1.utils.monitoring.metrics import (
    initialize_metrics,
    record_request_metric,
    record_error_metric,
    record_auth_metric,
    record_system_metric,
    get_metrics,
    get_metric_summary
)

from api.v1.utils.monitoring.alerts import (
    initialize_alerts,
    get_alerts,
    acknowledge_alert,
    resolve_alert
)

from api.v1.utils.monitoring.dashboards import (
    initialize_dashboards,
    get_dashboard_data
)

from api.v1.utils.monitoring.integration import (
    RequestMonitoringMiddleware,
    monitor_auth_event,
    monitor_system_health,
    setup_monitoring,
    init_app
)

__all__ = [
    'initialize_metrics',
    'record_request_metric',
    'record_error_metric',
    'record_auth_metric',
    'record_system_metric',
    'get_metrics',
    'get_metric_summary',
    'initialize_alerts',
    'get_alerts',
    'acknowledge_alert',
    'resolve_alert',
    'initialize_dashboards',
    'get_dashboard_data',
    'RequestMonitoringMiddleware',
    'monitor_auth_event',
    'monitor_system_health',
    'setup_monitoring',
    'init_app'
]
