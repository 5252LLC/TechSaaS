"""
Alerts System for TechSaaS Monitoring

This module provides alerting capabilities based on metrics thresholds
and anomaly detection to notify administrators of potential issues.
"""

import time
import threading
import json
import os
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from api.v1.utils.logging import get_logger
from api.v1.utils.monitoring.metrics import (
    get_metric_summary, 
    register_metric_hook,
    Metric, 
    TIME_WINDOW_5MIN
)

# Get logger for this module
logger = get_logger(__name__)

# Alert severity levels
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_CRITICAL = "critical"

# Alert statuses
STATUS_ACTIVE = "active"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_RESOLVED = "resolved"

@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    id: str
    name: str
    description: str
    metric_type: str
    metric_name: str
    condition: str  # >, <, >=, <=, ==, !=
    threshold: float
    window: int = TIME_WINDOW_5MIN
    severity: str = SEVERITY_WARNING
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        """Create rule from dictionary."""
        return cls(**data)

@dataclass
class Alert:
    """Alert generated from a rule."""
    id: str
    rule_id: str
    name: str
    description: str
    metric_type: str
    metric_name: str
    condition: str
    threshold: float
    actual_value: float
    severity: str
    status: str = STATUS_ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    acknowledged_by: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create alert from dictionary."""
        return cls(**data)

class AlertManager:
    """Manager for alert rules and generated alerts."""
    
    def __init__(self):
        """Initialize alert manager."""
        self._rules = {}  # id -> AlertRule
        self._alerts = {}  # id -> Alert
        self._lock = threading.RLock()
        self._check_interval = 60  # seconds
        self._storage_path = None
        self._alert_handlers = []  # List of functions to call when alerts are triggered
        self._alert_thread = None
        self._stop_event = threading.Event()
        self._initialized = False
    
    def initialize(self, storage_path: Optional[str] = None, check_interval: int = 60) -> None:
        """
        Initialize the alert manager.
        
        Args:
            storage_path: Directory to store alert data
            check_interval: Interval in seconds to check alerts
        """
        self._check_interval = check_interval
        
        if storage_path:
            self._storage_path = storage_path
            os.makedirs(storage_path, exist_ok=True)
            
            # Load existing rules and alerts
            self._load_rules()
            self._load_alerts()
        
        # Start alert checking thread
        self._start_alert_thread()
        
        # Register metric hook to check alerts on new metrics
        register_metric_hook(self._metric_hook)
        
        self._initialized = True
        logger.info(f"Alert manager initialized with storage_path={storage_path}, "
                   f"check_interval={check_interval}s")
    
    def _start_alert_thread(self) -> None:
        """Start the alert checking thread."""
        self._stop_event.clear()
        self._alert_thread = threading.Thread(target=self._alert_check_loop, daemon=True)
        self._alert_thread.start()
        logger.info("Alert checking thread started")
    
    def _alert_check_loop(self) -> None:
        """Background loop to periodically check alert rules."""
        while not self._stop_event.is_set():
            try:
                self.check_alert_rules()
            except Exception as e:
                logger.error(f"Error checking alert rules: {e}", exc_info=True)
            
            # Sleep until next check, but allow early termination
            self._stop_event.wait(self._check_interval)
    
    def shutdown(self) -> None:
        """Shutdown the alert manager and stop background threads."""
        if self._alert_thread and self._alert_thread.is_alive():
            self._stop_event.set()
            self._alert_thread.join(timeout=5)
            logger.info("Alert checking thread stopped")
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        with self._lock:
            self._rules[rule.id] = rule
            
            # Persist rules
            if self._storage_path:
                self._save_rules()
    
    def update_rule(self, rule_id: str, **kwargs) -> Optional[AlertRule]:
        """
        Update an existing alert rule.
        
        Args:
            rule_id: ID of rule to update
            **kwargs: Fields to update
            
        Returns:
            Updated rule or None if not found
        """
        with self._lock:
            if rule_id not in self._rules:
                return None
            
            rule = self._rules[rule_id]
            
            # Update fields
            for k, v in kwargs.items():
                if hasattr(rule, k):
                    setattr(rule, k, v)
            
            # Persist rules
            if self._storage_path:
                self._save_rules()
            
            return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        Delete an alert rule.
        
        Args:
            rule_id: ID of rule to delete
            
        Returns:
            True if rule was deleted, False if not found
        """
        with self._lock:
            if rule_id not in self._rules:
                return False
            
            del self._rules[rule_id]
            
            # Persist rules
            if self._storage_path:
                self._save_rules()
            
            return True
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        Get an alert rule by ID.
        
        Args:
            rule_id: ID of rule to retrieve
            
        Returns:
            Alert rule or None if not found
        """
        with self._lock:
            return self._rules.get(rule_id)
    
    def get_rules(self, enabled_only: bool = False) -> List[AlertRule]:
        """
        Get all alert rules.
        
        Args:
            enabled_only: Only return enabled rules
            
        Returns:
            List of alert rules
        """
        with self._lock:
            if enabled_only:
                return [r for r in self._rules.values() if r.enabled]
            else:
                return list(self._rules.values())
    
    def check_alert_rules(self) -> List[Alert]:
        """
        Check all alert rules against current metrics.
        
        Returns:
            List of new alerts that were triggered
        """
        new_alerts = []
        
        # Get enabled rules
        rules = self.get_rules(enabled_only=True)
        
        # Check each rule
        for rule in rules:
            try:
                # Get metrics for rule
                metrics = get_metric_summary(rule.metric_type, rule.window)
                
                # Skip if metric not found
                if not metrics or rule.metric_name not in metrics:
                    continue
                
                # Get metric value
                value = metrics[rule.metric_name]
                
                # Check condition
                triggered = False
                if rule.condition == ">":
                    triggered = value > rule.threshold
                elif rule.condition == ">=":
                    triggered = value >= rule.threshold
                elif rule.condition == "<":
                    triggered = value < rule.threshold
                elif rule.condition == "<=":
                    triggered = value <= rule.threshold
                elif rule.condition == "==":
                    triggered = value == rule.threshold
                elif rule.condition == "!=":
                    triggered = value != rule.threshold
                
                # If triggered and not already alerted, create alert
                if triggered and not self._is_already_alerted(rule.id):
                    alert = Alert(
                        id=f"alert_{int(time.time())}_{rule.id}",
                        rule_id=rule.id,
                        name=rule.name,
                        description=rule.description,
                        metric_type=rule.metric_type,
                        metric_name=rule.metric_name,
                        condition=rule.condition,
                        threshold=rule.threshold,
                        actual_value=value,
                        severity=rule.severity,
                        tags=rule.tags.copy()
                    )
                    
                    # Add alert
                    with self._lock:
                        self._alerts[alert.id] = alert
                    
                    # Call alert handlers
                    for handler in self._alert_handlers:
                        try:
                            handler(alert)
                        except Exception as e:
                            logger.error(f"Error in alert handler: {e}", exc_info=True)
                    
                    new_alerts.append(alert)
                    
                    # Log alert
                    logger.warning(f"Alert triggered: {alert.name} - {alert.description}", extra={
                        "alert_id": alert.id,
                        "rule_id": alert.rule_id,
                        "metric_type": alert.metric_type,
                        "metric_name": alert.metric_name,
                        "threshold": alert.threshold,
                        "actual_value": alert.actual_value,
                        "severity": alert.severity
                    })
                    
                    # Persist alerts
                    if self._storage_path:
                        self._save_alerts()
            except Exception as e:
                logger.error(f"Error checking rule {rule.id} - {rule.name}: {e}", exc_info=True)
        
        return new_alerts
    
    def _is_already_alerted(self, rule_id: str) -> bool:
        """
        Check if a rule already has an active alert.
        
        Args:
            rule_id: ID of rule to check
            
        Returns:
            True if rule has an active alert
        """
        with self._lock:
            for alert in self._alerts.values():
                if alert.rule_id == rule_id and alert.status == STATUS_ACTIVE:
                    return True
            return False
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of alert to acknowledge
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            Updated alert or None if not found
        """
        with self._lock:
            if alert_id not in self._alerts:
                return None
            
            alert = self._alerts[alert_id]
            
            # Only acknowledge active alerts
            if alert.status != STATUS_ACTIVE:
                return alert
            
            # Update alert
            alert.status = STATUS_ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = time.time()
            
            # Persist alerts
            if self._storage_path:
                self._save_alerts()
            
            return alert
    
    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of alert to resolve
            
        Returns:
            Updated alert or None if not found
        """
        with self._lock:
            if alert_id not in self._alerts:
                return None
            
            alert = self._alerts[alert_id]
            
            # Only resolve active or acknowledged alerts
            if alert.status == STATUS_RESOLVED:
                return alert
            
            # Update alert
            alert.status = STATUS_RESOLVED
            alert.resolved_at = time.time()
            alert.updated_at = time.time()
            
            # Persist alerts
            if self._storage_path:
                self._save_alerts()
            
            return alert
    
    def get_alerts(self, 
                 status: Optional[str] = None, 
                 severity: Optional[str] = None,
                 rule_id: Optional[str] = None,
                 start_time: Optional[float] = None,
                 end_time: Optional[float] = None,
                 limit: int = 100) -> List[Alert]:
        """
        Get alerts matching the specified criteria.
        
        Args:
            status: Filter by status
            severity: Filter by severity
            rule_id: Filter by rule ID
            start_time: Filter by creation time (>=)
            end_time: Filter by creation time (<=)
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts
        """
        with self._lock:
            alerts = list(self._alerts.values())
            
            # Apply filters
            if status is not None:
                alerts = [a for a in alerts if a.status == status]
            
            if severity is not None:
                alerts = [a for a in alerts if a.severity == severity]
            
            if rule_id is not None:
                alerts = [a for a in alerts if a.rule_id == rule_id]
            
            if start_time is not None:
                alerts = [a for a in alerts if a.created_at >= start_time]
            
            if end_time is not None:
                alerts = [a for a in alerts if a.created_at <= end_time]
            
            # Sort by created_at (newest first)
            alerts.sort(key=lambda a: a.created_at, reverse=True)
            
            # Apply limit
            return alerts[:limit]
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: ID of alert to retrieve
            
        Returns:
            Alert or None if not found
        """
        with self._lock:
            return self._alerts.get(alert_id)
    
    def register_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Register a handler to be called when an alert is triggered.
        
        Args:
            handler: Function to call with the new alert
        """
        self._alert_handlers.append(handler)
    
    def _metric_hook(self, metric: Metric) -> None:
        """
        Hook for new metrics.
        
        Args:
            metric: New metric
        """
        # Check if we need to immediately check rules
        # This is useful for real-time alerting on critical metrics
        if metric.type == "error" or (hasattr(metric, "status_code") and getattr(metric, "status_code", 0) >= 500):
            self.check_alert_rules()
    
    def _save_rules(self) -> None:
        """Save rules to disk."""
        if not self._storage_path:
            return
        
        try:
            # Create rules file
            filename = os.path.join(self._storage_path, "alert_rules.json")
            
            # Convert rules to dictionaries
            rules_data = {rule_id: rule.to_dict() for rule_id, rule in self._rules.items()}
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(rules_data, f, indent=2)
                
            logger.info(f"Saved {len(rules_data)} alert rules to {filename}")
        except Exception as e:
            logger.error(f"Error saving alert rules: {e}", exc_info=True)
    
    def _load_rules(self) -> None:
        """Load rules from disk."""
        if not self._storage_path:
            return
        
        filename = os.path.join(self._storage_path, "alert_rules.json")
        
        if not os.path.exists(filename):
            return
        
        try:
            # Read file
            with open(filename, 'r') as f:
                rules_data = json.load(f)
            
            # Load rules
            for rule_id, rule_data in rules_data.items():
                rule = AlertRule.from_dict(rule_data)
                self._rules[rule_id] = rule
                
            logger.info(f"Loaded {len(self._rules)} alert rules from {filename}")
        except Exception as e:
            logger.error(f"Error loading alert rules: {e}", exc_info=True)
    
    def _save_alerts(self) -> None:
        """Save alerts to disk."""
        if not self._storage_path:
            return
        
        try:
            # Create alerts file
            filename = os.path.join(self._storage_path, "alerts.json")
            
            # Convert alerts to dictionaries
            alerts_data = {alert_id: alert.to_dict() for alert_id, alert in self._alerts.items()}
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(alerts_data, f, indent=2)
                
            logger.info(f"Saved {len(alerts_data)} alerts to {filename}")
        except Exception as e:
            logger.error(f"Error saving alerts: {e}", exc_info=True)
    
    def _load_alerts(self) -> None:
        """Load alerts from disk."""
        if not self._storage_path:
            return
        
        filename = os.path.join(self._storage_path, "alerts.json")
        
        if not os.path.exists(filename):
            return
        
        try:
            # Read file
            with open(filename, 'r') as f:
                alerts_data = json.load(f)
            
            # Load alerts
            for alert_id, alert_data in alerts_data.items():
                alert = Alert.from_dict(alert_data)
                self._alerts[alert_id] = alert
                
            logger.info(f"Loaded {len(self._alerts)} alerts from {filename}")
        except Exception as e:
            logger.error(f"Error loading alerts: {e}", exc_info=True)

# Global instance
_alert_manager = AlertManager()

# Default notification handlers
def email_alert_handler(alert: Alert, smtp_config: Dict[str, Any]) -> None:
    """
    Send an alert via email.
    
    Args:
        alert: Alert to send
        smtp_config: SMTP configuration
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from']
        msg['To'] = smtp_config['to']
        msg['Subject'] = f"[{alert.severity.upper()}] TechSaaS Alert: {alert.name}"
        
        # Build email body
        body = f"""
        <html>
        <body>
        <h2>{alert.name}</h2>
        <p><strong>Description:</strong> {alert.description}</p>
        <p><strong>Severity:</strong> {alert.severity}</p>
        <p><strong>Metric:</strong> {alert.metric_type}.{alert.metric_name}</p>
        <p><strong>Condition:</strong> {alert.condition} {alert.threshold}</p>
        <p><strong>Actual Value:</strong> {alert.actual_value}</p>
        <p><strong>Triggered At:</strong> {datetime.fromtimestamp(alert.created_at).strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to server and send
        server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
        if smtp_config.get('use_tls', False):
            server.starttls()
        
        if 'username' in smtp_config and 'password' in smtp_config:
            server.login(smtp_config['username'], smtp_config['password'])
        
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Sent email alert: {alert.id} - {alert.name}")
    except Exception as e:
        logger.error(f"Error sending email alert: {e}", exc_info=True)

def webhook_alert_handler(alert: Alert, webhook_url: str) -> None:
    """
    Send an alert via webhook.
    
    Args:
        alert: Alert to send
        webhook_url: Webhook URL
    """
    try:
        # Prepare payload
        payload = {
            'id': alert.id,
            'name': alert.name,
            'description': alert.description,
            'severity': alert.severity,
            'metric_type': alert.metric_type,
            'metric_name': alert.metric_name,
            'condition': alert.condition,
            'threshold': alert.threshold,
            'actual_value': alert.actual_value,
            'created_at': alert.created_at,
            'timestamp': datetime.fromtimestamp(alert.created_at).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send request
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        
        logger.info(f"Sent webhook alert: {alert.id} - {alert.name}")
    except Exception as e:
        logger.error(f"Error sending webhook alert: {e}", exc_info=True)

def slack_alert_handler(alert: Alert, webhook_url: str) -> None:
    """
    Send an alert to Slack.
    
    Args:
        alert: Alert to send
        webhook_url: Slack webhook URL
    """
    try:
        # Determine color based on severity
        if alert.severity == SEVERITY_CRITICAL:
            color = "#FF0000"  # Red
        elif alert.severity == SEVERITY_ERROR:
            color = "#FFA500"  # Orange
        elif alert.severity == SEVERITY_WARNING:
            color = "#FFFF00"  # Yellow
        else:
            color = "#36A64F"  # Green
        
        # Prepare payload
        payload = {
            "attachments": [
                {
                    "fallback": f"[{alert.severity.upper()}] {alert.name}",
                    "color": color,
                    "title": f"[{alert.severity.upper()}] {alert.name}",
                    "text": alert.description,
                    "fields": [
                        {
                            "title": "Metric",
                            "value": f"{alert.metric_type}.{alert.metric_name}",
                            "short": True
                        },
                        {
                            "title": "Condition",
                            "value": f"{alert.condition} {alert.threshold}",
                            "short": True
                        },
                        {
                            "title": "Actual Value",
                            "value": str(alert.actual_value),
                            "short": True
                        },
                        {
                            "title": "Triggered At",
                            "value": datetime.fromtimestamp(alert.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "footer": "TechSaaS Monitoring",
                    "ts": int(alert.created_at)
                }
            ]
        }
        
        # Send request
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        
        logger.info(f"Sent Slack alert: {alert.id} - {alert.name}")
    except Exception as e:
        logger.error(f"Error sending Slack alert: {e}", exc_info=True)

# Public API functions
def initialize_alerts(storage_path: Optional[str] = None, check_interval: int = 60) -> None:
    """
    Initialize the alerts system.
    
    Args:
        storage_path: Directory to store alert data
        check_interval: Interval in seconds to check alerts
    """
    _alert_manager.initialize(storage_path, check_interval)

def add_alert_rule(rule: AlertRule) -> None:
    """
    Add an alert rule.
    
    Args:
        rule: Alert rule to add
    """
    _alert_manager.add_rule(rule)

def update_alert_rule(rule_id: str, **kwargs) -> Optional[AlertRule]:
    """
    Update an existing alert rule.
    
    Args:
        rule_id: ID of rule to update
        **kwargs: Fields to update
        
    Returns:
        Updated rule or None if not found
    """
    return _alert_manager.update_rule(rule_id, **kwargs)

def delete_alert_rule(rule_id: str) -> bool:
    """
    Delete an alert rule.
    
    Args:
        rule_id: ID of rule to delete
        
    Returns:
        True if rule was deleted, False if not found
    """
    return _alert_manager.delete_rule(rule_id)

def get_alert_rules(enabled_only: bool = False) -> List[Dict[str, Any]]:
    """
    Get all alert rules.
    
    Args:
        enabled_only: Only return enabled rules
        
    Returns:
        List of alert rules as dictionaries
    """
    rules = _alert_manager.get_rules(enabled_only)
    return [rule.to_dict() for rule in rules]

def get_alerts(status: Optional[str] = None, 
             severity: Optional[str] = None,
             rule_id: Optional[str] = None,
             start_time: Optional[float] = None,
             end_time: Optional[float] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get alerts matching the specified criteria.
    
    Args:
        status: Filter by status
        severity: Filter by severity
        rule_id: Filter by rule ID
        start_time: Filter by creation time (>=)
        end_time: Filter by creation time (<=)
        limit: Maximum number of alerts to return
        
    Returns:
        List of alerts as dictionaries
    """
    alerts = _alert_manager.get_alerts(status, severity, rule_id, start_time, end_time, limit)
    return [alert.to_dict() for alert in alerts]

def acknowledge_alert(alert_id: str, acknowledged_by: str) -> Optional[Dict[str, Any]]:
    """
    Acknowledge an alert.
    
    Args:
        alert_id: ID of alert to acknowledge
        acknowledged_by: User who acknowledged the alert
        
    Returns:
        Updated alert as dictionary or None if not found
    """
    alert = _alert_manager.acknowledge_alert(alert_id, acknowledged_by)
    return alert.to_dict() if alert else None

def resolve_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Resolve an alert.
    
    Args:
        alert_id: ID of alert to resolve
        
    Returns:
        Updated alert as dictionary or None if not found
    """
    alert = _alert_manager.resolve_alert(alert_id)
    return alert.to_dict() if alert else None

def check_alert_thresholds() -> List[Dict[str, Any]]:
    """
    Check all alert rules against current metrics.
    
    Returns:
        List of new alerts that were triggered as dictionaries
    """
    alerts = _alert_manager.check_alert_rules()
    return [alert.to_dict() for alert in alerts]

def register_alert_handler(handler: Callable[[Alert], None]) -> None:
    """
    Register a handler to be called when an alert is triggered.
    
    Args:
        handler: Function to call with the new alert
    """
    _alert_manager.register_alert_handler(handler)

def send_alert(alert_type: str, name: str, description: str, 
             severity: str = SEVERITY_WARNING,
             metric_type: str = "",
             metric_name: str = "",
             value: float = 0,
             tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Manually create and send an alert.
    
    Args:
        alert_type: Type of alert
        name: Alert name
        description: Alert description
        severity: Alert severity
        metric_type: Metric type
        metric_name: Metric name
        value: Metric value
        tags: Additional tags
        
    Returns:
        Created alert as dictionary
    """
    alert = Alert(
        id=f"manual_alert_{int(time.time())}",
        rule_id="manual",
        name=name,
        description=description,
        metric_type=metric_type,
        metric_name=metric_name,
        condition="manual",
        threshold=0,
        actual_value=value,
        severity=severity,
        tags=tags or {}
    )
    
    # Call alert handlers
    for handler in _alert_manager._alert_handlers:
        try:
            handler(alert)
        except Exception as e:
            logger.error(f"Error in alert handler: {e}", exc_info=True)
    
    # Add to alerts
    with _alert_manager._lock:
        _alert_manager._alerts[alert.id] = alert
        
        # Persist alerts
        if _alert_manager._storage_path:
            _alert_manager._save_alerts()
    
    # Log alert
    logger.warning(f"Manual alert sent: {alert.name} - {alert.description}", extra={
        "alert_id": alert.id,
        "alert_type": alert_type,
        "severity": alert.severity
    })
    
    return alert.to_dict()
