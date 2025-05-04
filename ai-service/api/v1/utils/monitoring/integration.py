"""
Monitoring System Integration for TechSaaS

This module provides integration functions to connect the monitoring system
with the main Flask application and other components of TechSaaS.
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from flask import Flask, request, g, current_app, Blueprint, jsonify, Response
import socket
import json
import psutil
from functools import wraps

from api.v1.utils.logging import get_logger
from api.v1.utils.monitoring.metrics import (
    initialize_metrics,
    record_request_metric,
    record_error_metric,
    record_auth_metric,
    record_system_metric,
    get_metric_summary,
    get_metrics
)
from api.v1.utils.monitoring.alerts import (
    initialize_alerts,
    add_alert_rule,
    get_alert_rules,
    get_alerts,
    acknowledge_alert,
    resolve_alert,
    check_alert_thresholds,
    send_alert,
    AlertRule,
    SEVERITY_WARNING,
    SEVERITY_ERROR,
    SEVERITY_CRITICAL
)
from api.v1.utils.monitoring.dashboards import (
    initialize_dashboards,
    add_dashboard_config,
    get_dashboard_data,
    get_dashboard_configs,
    DEFAULT_DASHBOARDS
)

# Get logger for this module
logger = get_logger(__name__)

class RequestMonitoringMiddleware:
    """
    Middleware for monitoring Flask requests and responses.
    
    This middleware captures metrics about API requests including response times,
    status codes, and error rates.
    """
    
    def __init__(self, app: Flask):
        """
        Initialize the middleware.
        
        Args:
            app: Flask application
        """
        self.app = app
        self._setup_middleware()
        logger.info("Request monitoring middleware initialized")
    
    def _setup_middleware(self) -> None:
        """
        Set up the middleware.
        
        This method registers hooks for before_request, after_request, and
        teardown_request to capture request metrics.
        """
        @self.app.before_request
        def before_request() -> None:
            """Store start time for request timing."""
            g.start_time = time.time()
            g.request_id = getattr(request, 'id', str(time.time()))
        
        @self.app.after_request
        def after_request(response: Response) -> Response:
            """
            Record request metrics after each request.
            
            Args:
                response: Flask response
                
            Returns:
                Original response
            """
            try:
                # Calculate response time
                if hasattr(g, 'start_time'):
                    response_time = time.time() - g.start_time
                else:
                    response_time = 0
                
                # Get user ID if available
                user_id = ""
                if hasattr(g, 'user') and hasattr(g.user, 'id'):
                    user_id = g.user.id
                
                # Get request path and method
                path = request.path
                method = request.method
                
                # Record request metric
                record_request_metric(
                    name="api_request",
                    endpoint=path,
                    method=method,
                    status_code=response.status_code,
                    response_time=response_time,
                    client_ip=request.remote_addr,
                    user_id=user_id,
                    tags={"host": socket.gethostname()}
                )
                
                # Record specific error metrics for 4xx and 5xx responses
                if response.status_code >= 400:
                    error_type = "client_error" if response.status_code < 500 else "server_error"
                    
                    record_error_metric(
                        name="api_error",
                        error_type=error_type,
                        message=f"HTTP {response.status_code}",
                        endpoint=path,
                        method=method,
                        client_ip=request.remote_addr,
                        user_id=user_id,
                        tags={"status_code": str(response.status_code)}
                    )
            except Exception as e:
                logger.error(f"Error recording request metric: {e}", exc_info=True)
            
            return response
        
        @self.app.teardown_request
        def teardown_request(exception: Optional[Exception]) -> None:
            """
            Record exception metrics for unhandled exceptions.
            
            Args:
                exception: Unhandled exception if any
            """
            if exception:
                try:
                    # Get request path and method
                    path = request.path
                    method = request.method
                    
                    # Get user ID if available
                    user_id = ""
                    if hasattr(g, 'user') and hasattr(g.user, 'id'):
                        user_id = g.user.id
                    
                    # Record error metric
                    record_error_metric(
                        name="unhandled_exception",
                        error_type=exception.__class__.__name__,
                        message=str(exception),
                        endpoint=path,
                        method=method,
                        client_ip=request.remote_addr,
                        user_id=user_id,
                        tags={"host": socket.gethostname()}
                    )
                    
                    # Send alert for critical errors
                    try:
                        send_alert(
                            alert_type="exception",
                            name=f"Unhandled Exception: {exception.__class__.__name__}",
                            description=f"An unhandled exception occurred: {str(exception)}",
                            severity=SEVERITY_ERROR,
                            metric_type="error",
                            metric_name="unhandled_exception",
                            value=1,
                            tags={"endpoint": path, "method": method}
                        )
                    except Exception as e:
                        logger.error(f"Error sending exception alert: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Error recording exception metric: {e}", exc_info=True)

def monitor_auth_event(auth_type: str, success: bool, user_id: str = "", 
                    client_ip: str = "", tags: Optional[Dict[str, str]] = None) -> None:
    """
    Monitor an authentication event.
    
    This function records metrics for authentication events such as login, logout,
    token refresh, etc. It also triggers alerts for failed authentication attempts.
    
    Args:
        auth_type: Type of authentication event
        success: Whether the authentication was successful
        user_id: ID of the user
        client_ip: Client IP address
        tags: Additional tags
    """
    try:
        # Record auth metric
        record_auth_metric(
            name="auth_attempt",
            auth_type=auth_type,
            success=success,
            user_id=user_id,
            client_ip=client_ip,
            tags=tags or {}
        )
        
        # Alert on failed authentication if user_id provided
        if not success and user_id:
            # Check if we should send an alert for repeated failures
            recent_failures = get_metrics(
                metric_type="auth",
                filters={
                    "name": "auth_attempt",
                    "auth_type": auth_type,
                    "user_id": user_id,
                    "success": False
                },
                start_time=time.time() - 3600,  # Last hour
                limit=10
            )
            
            # Alert if multiple failures
            if len(recent_failures) >= 3:
                send_alert(
                    alert_type="auth",
                    name=f"Multiple Failed Authentication Attempts",
                    description=f"User {user_id} has failed {len(recent_failures)} "
                              f"{auth_type} attempts in the last hour.",
                    severity=SEVERITY_WARNING,
                    metric_type="auth",
                    metric_name="auth_attempt",
                    value=len(recent_failures),
                    tags={"user_id": user_id, "auth_type": auth_type}
                )
    except Exception as e:
        logger.error(f"Error monitoring auth event: {e}", exc_info=True)

def monitor_system_health(app: Flask) -> None:
    """
    Monitor system health metrics.
    
    This function collects various system metrics like CPU usage, memory usage,
    disk usage, etc. and records them for monitoring.
    
    Args:
        app: Flask application
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        record_system_metric(
            name="cpu_usage",
            value=cpu_percent,
            component="system",
            host=socket.gethostname()
        )
        
        # Get memory usage
        memory = psutil.virtual_memory()
        record_system_metric(
            name="memory_usage",
            value=memory.percent,
            component="system",
            host=socket.gethostname()
        )
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        record_system_metric(
            name="disk_usage",
            value=disk.percent,
            component="system",
            host=socket.gethostname()
        )
        
        # Alert on high resource usage
        if cpu_percent > 80:
            send_alert(
                alert_type="system",
                name="High CPU Usage",
                description=f"CPU usage is at {cpu_percent}%, which is above the threshold of 80%.",
                severity=SEVERITY_WARNING,
                metric_type="system",
                metric_name="cpu_usage",
                value=cpu_percent
            )
        
        if memory.percent > 80:
            send_alert(
                alert_type="system",
                name="High Memory Usage",
                description=f"Memory usage is at {memory.percent}%, which is above the threshold of 80%.",
                severity=SEVERITY_WARNING,
                metric_type="system",
                metric_name="memory_usage",
                value=memory.percent
            )
        
        if disk.percent > 80:
            send_alert(
                alert_type="system",
                name="High Disk Usage",
                description=f"Disk usage is at {disk.percent}%, which is above the threshold of 80%.",
                severity=SEVERITY_WARNING,
                metric_type="system",
                metric_name="disk_usage",
                value=disk.percent
            )
    except Exception as e:
        logger.error(f"Error monitoring system health: {e}", exc_info=True)

def create_monitoring_blueprint() -> Blueprint:
    """
    Create a Flask blueprint for monitoring endpoints.
    
    This function creates a blueprint with routes for accessing metrics,
    alerts, and dashboards.
    
    Returns:
        Flask blueprint
    """
    monitoring_bp = Blueprint('monitoring', __name__)
    
    @monitoring_bp.route('/api/monitoring/metrics', methods=['GET'])
    def get_metrics_endpoint():
        """
        Get metrics data.
        
        Query parameters:
        - metric_type: Type of metrics to retrieve
        - start_time: Start time as timestamp
        - end_time: End time as timestamp
        - limit: Maximum number of metrics to return
        
        Returns:
            JSON response with metrics data
        """
        try:
            # Get parameters
            metric_type = request.args.get('metric_type')
            
            start_time = request.args.get('start_time')
            if start_time:
                start_time = float(start_time)
            
            end_time = request.args.get('end_time')
            if end_time:
                end_time = float(end_time)
            
            limit = request.args.get('limit', 100)
            limit = int(limit)
            
            # Get metrics
            metrics_data = get_metrics(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # Get aggregated metrics
            window = request.args.get('window', '300')
            window = int(window)
            
            aggregated_metrics = get_metric_summary(metric_type, window)
            
            return jsonify({
                'status': 'success',
                'metrics': metrics_data,
                'aggregated_metrics': aggregated_metrics,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in metrics endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/alerts', methods=['GET'])
    def get_alerts_endpoint():
        """
        Get alerts data.
        
        Query parameters:
        - status: Filter by status
        - severity: Filter by severity
        - rule_id: Filter by rule ID
        - start_time: Start time as timestamp
        - end_time: End time as timestamp
        - limit: Maximum number of alerts to return
        
        Returns:
            JSON response with alerts data
        """
        try:
            # Get parameters
            status = request.args.get('status')
            severity = request.args.get('severity')
            rule_id = request.args.get('rule_id')
            
            start_time = request.args.get('start_time')
            if start_time:
                start_time = float(start_time)
            
            end_time = request.args.get('end_time')
            if end_time:
                end_time = float(end_time)
            
            limit = request.args.get('limit', 100)
            limit = int(limit)
            
            # Get alerts
            alerts_data = get_alerts(
                status=status,
                severity=severity,
                rule_id=rule_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            return jsonify({
                'status': 'success',
                'alerts': alerts_data,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in alerts endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/alerts/<alert_id>/acknowledge', methods=['POST'])
    def acknowledge_alert_endpoint(alert_id):
        """
        Acknowledge an alert.
        
        Path parameters:
        - alert_id: ID of alert to acknowledge
        
        JSON body:
        - acknowledged_by: User who acknowledged the alert
        
        Returns:
            JSON response with updated alert
        """
        try:
            # Get parameters
            data = request.json or {}
            acknowledged_by = data.get('acknowledged_by', 'unknown')
            
            # Acknowledge alert
            updated_alert = acknowledge_alert(alert_id, acknowledged_by)
            
            if not updated_alert:
                return jsonify({
                    'status': 'error',
                    'message': f'Alert not found: {alert_id}'
                }), 404
            
            return jsonify({
                'status': 'success',
                'alert': updated_alert,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in acknowledge alert endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/alerts/<alert_id>/resolve', methods=['POST'])
    def resolve_alert_endpoint(alert_id):
        """
        Resolve an alert.
        
        Path parameters:
        - alert_id: ID of alert to resolve
        
        Returns:
            JSON response with updated alert
        """
        try:
            # Resolve alert
            updated_alert = resolve_alert(alert_id)
            
            if not updated_alert:
                return jsonify({
                    'status': 'error',
                    'message': f'Alert not found: {alert_id}'
                }), 404
            
            return jsonify({
                'status': 'success',
                'alert': updated_alert,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in resolve alert endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/dashboards', methods=['GET'])
    def get_dashboards_endpoint():
        """
        Get available dashboards.
        
        Returns:
            JSON response with dashboard configurations
        """
        try:
            # Get dashboards
            dashboards = get_dashboard_configs()
            
            return jsonify({
                'status': 'success',
                'dashboards': dashboards,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in dashboards endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/dashboards/<dashboard_id>', methods=['GET'])
    def get_dashboard_data_endpoint(dashboard_id):
        """
        Get data for a specific dashboard.
        
        Path parameters:
        - dashboard_id: ID of dashboard
        
        Query parameters:
        - Various dashboard parameters
        
        Returns:
            JSON response with dashboard data
        """
        try:
            # Get parameters
            params = {}
            for key, value in request.args.items():
                # Convert some types
                if key in ['start_time', 'end_time']:
                    params[key] = float(value)
                elif key in ['limit', 'window']:
                    params[key] = int(value)
                else:
                    params[key] = value
            
            # Get dashboard data
            dashboard_data = get_dashboard_data(dashboard_id, params)
            
            return jsonify({
                'status': 'success',
                'dashboard': dashboard_data,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in dashboard data endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @monitoring_bp.route('/api/monitoring/health', methods=['GET'])
    def health_check_endpoint():
        """
        Perform a system health check.
        
        Returns:
            JSON response with health status
        """
        try:
            # Collect system health metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get recent errors
            recent_errors = get_metrics(
                metric_type="error",
                start_time=time.time() - 300,  # Last 5 minutes
                limit=10
            )
            
            # Get active alerts
            active_alerts = get_alerts(status="active", limit=10)
            
            # Check thresholds
            system_status = "healthy"
            if cpu_percent > 80 or memory.percent > 80 or disk.percent > 80:
                system_status = "warning"
            
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                system_status = "critical"
            
            if len(active_alerts) > 5:
                system_status = "warning"
            
            if len([a for a in active_alerts if a.get('severity') == SEVERITY_CRITICAL]) > 0:
                system_status = "critical"
            
            return jsonify({
                'status': 'success',
                'health': {
                    'status': system_status,
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory.percent,
                    'disk_usage': disk.percent,
                    'recent_error_count': len(recent_errors),
                    'active_alert_count': len(active_alerts)
                },
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error in health check endpoint: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    return monitoring_bp

def setup_monitoring(app: Flask, 
                   storage_path: Optional[str] = None, 
                   check_interval: int = 60,
                   enable_system_monitoring: bool = True,
                   system_monitoring_interval: int = 300) -> None:
    """
    Set up the monitoring system.
    
    This function initializes the metrics, alerts, and dashboards systems and
    configures them based on the provided parameters.
    
    Args:
        app: Flask application
        storage_path: Directory to store monitoring data
        check_interval: Interval in seconds to check alerts
        enable_system_monitoring: Whether to enable system monitoring
        system_monitoring_interval: Interval in seconds to check system health
    """
    # Create storage path if it doesn't exist
    if storage_path:
        os.makedirs(storage_path, exist_ok=True)
        
        # Create subdirectories
        metrics_path = os.path.join(storage_path, 'metrics')
        alerts_path = os.path.join(storage_path, 'alerts')
        dashboards_path = os.path.join(storage_path, 'dashboards')
        
        os.makedirs(metrics_path, exist_ok=True)
        os.makedirs(alerts_path, exist_ok=True)
        os.makedirs(dashboards_path, exist_ok=True)
    else:
        metrics_path = None
        alerts_path = None
        dashboards_path = None
    
    # Initialize metrics
    initialize_metrics(metrics_path)
    logger.info("Metrics system initialized")
    
    # Initialize alerts
    initialize_alerts(alerts_path, check_interval)
    logger.info("Alerts system initialized")
    
    # Initialize dashboards
    initialize_dashboards(dashboards_path)
    logger.info("Dashboards system initialized")
    
    # Add default dashboard configs
    for dashboard_id, config in DEFAULT_DASHBOARDS.items():
        add_dashboard_config(dashboard_id, config)
    logger.info(f"Added {len(DEFAULT_DASHBOARDS)} default dashboard configurations")
    
    # Add default alert rules
    _add_default_alert_rules()
    
    # Set up monitoring middleware
    app.monitoring_middleware = RequestMonitoringMiddleware(app)
    
    # Register monitoring blueprint
    monitoring_bp = create_monitoring_blueprint()
    app.register_blueprint(monitoring_bp)
    logger.info("Monitoring blueprint registered")
    
    # Set up system monitoring if enabled
    if enable_system_monitoring:
        import threading
        
        def system_monitoring_task():
            while True:
                try:
                    monitor_system_health(app)
                except Exception as e:
                    logger.error(f"Error in system monitoring task: {e}", exc_info=True)
                
                time.sleep(system_monitoring_interval)
        
        # Start system monitoring thread
        system_thread = threading.Thread(target=system_monitoring_task, daemon=True)
        system_thread.start()
        logger.info(f"System monitoring started with interval: {system_monitoring_interval}s")
    
    logger.info("Monitoring system setup complete")

def _add_default_alert_rules() -> None:
    """Add default alert rules."""
    # API error rate alert
    add_alert_rule(AlertRule(
        id="api_error_rate",
        name="High API Error Rate",
        description="Alert when the API error rate exceeds 5% over 5 minutes",
        metric_type="request",
        metric_name="api_request_300s_error_rate",
        condition=">",
        threshold=0.05,
        severity=SEVERITY_WARNING
    ))
    
    # High response time alert
    add_alert_rule(AlertRule(
        id="api_response_time",
        name="High API Response Time",
        description="Alert when the 90th percentile response time exceeds 1 second",
        metric_type="request",
        metric_name="api_request_300s_p90",
        condition=">",
        threshold=1.0,
        severity=SEVERITY_WARNING
    ))
    
    # Auth failure alert
    add_alert_rule(AlertRule(
        id="auth_failure_rate",
        name="High Authentication Failure Rate",
        description="Alert when the authentication success rate falls below 80%",
        metric_type="auth",
        metric_name="auth_attempt_300s_success_rate",
        condition="<",
        threshold=0.8,
        severity=SEVERITY_WARNING
    ))
    
    # System CPU usage alert
    add_alert_rule(AlertRule(
        id="high_cpu_usage",
        name="High CPU Usage",
        description="Alert when CPU usage exceeds 80%",
        metric_type="system",
        metric_name="cpu_usage_300s_avg",
        condition=">",
        threshold=80.0,
        severity=SEVERITY_WARNING
    ))
    
    # System memory usage alert
    add_alert_rule(AlertRule(
        id="high_memory_usage",
        name="High Memory Usage",
        description="Alert when memory usage exceeds 80%",
        metric_type="system",
        metric_name="memory_usage_300s_avg",
        condition=">",
        threshold=80.0,
        severity=SEVERITY_WARNING
    ))
    
    # System disk usage alert
    add_alert_rule(AlertRule(
        id="high_disk_usage",
        name="High Disk Usage",
        description="Alert when disk usage exceeds 80%",
        metric_type="system",
        metric_name="disk_usage_300s_avg",
        condition=">",
        threshold=80.0,
        severity=SEVERITY_WARNING
    ))
    
    logger.info("Added default alert rules")

def init_app(app: Flask) -> None:
    """
    Initialize monitoring for a Flask application.
    
    This function should be called during application setup to configure
    the monitoring system with the Flask app.
    
    Args:
        app: Flask application to initialize
    """
    # Get configuration from app config
    storage_path = app.config.get('MONITORING_STORAGE_PATH')
    check_interval = app.config.get('MONITORING_CHECK_INTERVAL', 60)
    enable_system_monitoring = app.config.get('ENABLE_SYSTEM_MONITORING', True)
    system_monitoring_interval = app.config.get('SYSTEM_MONITORING_INTERVAL', 300)
    
    # Set up monitoring
    setup_monitoring(
        app, 
        storage_path, 
        check_interval, 
        enable_system_monitoring,
        system_monitoring_interval
    )
