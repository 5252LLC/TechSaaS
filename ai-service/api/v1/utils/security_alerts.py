"""
Security Alerts Module

This module provides real-time alerting capabilities for security events
detected in the audit trail. It integrates with the notification system
to deliver alerts through various channels (email, SMS, in-app).
"""

import logging
import json
from datetime import datetime, timezone, UTC
from flask import current_app

from api.v1.utils.audit_trail import AuditEvent, audit_security_event
from api.v1.utils.notification_service import notification_service
from api.v1.utils.notification_queue import notification_queue

# Setup logger
logger = logging.getLogger(__name__)

# Define security event severity levels and their corresponding alert priorities
SEVERITY_PRIORITY_MAP = {
    'critical': 'high',
    'high': 'high',
    'medium': 'normal',
    'low': 'low',
    'info': None  # Don't alert for info-level events
}

# Define events that should trigger alerts
ALERT_TRIGGERS = {
    # Authentication events
    'failed_login_attempts': {
        'event_type': AuditEvent.USER_AUTHENTICATION,
        'action': 'login',
        'outcome': AuditEvent.OUTCOME_FAILURE,
        'threshold': 5,  # Number of failures within time_window
        'time_window': 10,  # Minutes
        'severity': 'high'
    },
    'admin_login': {
        'event_type': AuditEvent.USER_AUTHENTICATION, 
        'action': 'login',
        'outcome': AuditEvent.OUTCOME_SUCCESS,
        'admin_only': True,
        'severity': 'medium'
    },
    'password_change': {
        'event_type': AuditEvent.USER_AUTHENTICATION,
        'action': 'password_change',
        'severity': 'medium'
    },
    'account_lockout': {
        'event_type': AuditEvent.USER_AUTHENTICATION,
        'action': 'account_lockout',
        'severity': 'high'
    },
    
    # Authorization events
    'permission_change': {
        'event_type': AuditEvent.USER_AUTHORIZATION,
        'action': 'permission_change',
        'severity': 'high'
    },
    'role_change': {
        'event_type': AuditEvent.USER_AUTHORIZATION,
        'action': 'role_change',
        'severity': 'high'
    },
    'unauthorized_access': {
        'event_type': AuditEvent.USER_AUTHORIZATION,
        'action': 'access_denied',
        'threshold': 3,
        'time_window': 10,
        'severity': 'high'
    },
    
    # Data events
    'sensitive_data_access': {
        'event_type': AuditEvent.DATA_ACCESS,
        'resource_type': 'sensitive',
        'severity': 'medium'
    },
    'bulk_data_export': {
        'event_type': AuditEvent.DATA_ACCESS,
        'action': 'export',
        'severity': 'medium'
    },
    'data_deletion': {
        'event_type': AuditEvent.DATA_MODIFICATION,
        'action': 'delete',
        'severity': 'high'
    },
    
    # System events
    'config_change': {
        'event_type': AuditEvent.SYSTEM_CHANGE,
        'severity': 'high'
    },
    'api_key_creation': {
        'event_type': AuditEvent.ADMIN_ACTION,
        'action': 'api_key_created',
        'severity': 'high'
    },
    
    # Security specific events
    'security_event': {
        'event_type': AuditEvent.SECURITY_EVENT,
        'severity': 'critical'
    }
}

def is_alert_needed(event_data, trigger_config):
    """
    Determine if an alert is needed based on the event and trigger configuration.
    
    Args:
        event_data (dict): The audit event data
        trigger_config (dict): The trigger configuration
        
    Returns:
        bool: True if alert should be sent, False otherwise
    """
    # Check basic event properties
    for prop in ['event_type', 'action', 'outcome', 'resource_type']:
        if prop in trigger_config and prop in event_data:
            if event_data[prop] != trigger_config[prop]:
                return False
    
    # Check admin-only flag
    if trigger_config.get('admin_only') and event_data.get('actor_type') != 'admin':
        return False
    
    # Check for threshold-based alerts
    if 'threshold' in trigger_config:
        # This would require querying past events, 
        # which should be implemented by checking the audit storage
        # For now, we'll implement a simplified version
        threshold_met = True  # Simplified for demonstration
        if not threshold_met:
            return False
    
    # If we passed all checks, alert is needed
    return True

def get_alert_severity(event_data, trigger_config):
    """
    Determine the severity of an alert based on the event data and trigger configuration.
    
    Args:
        event_data (dict): The audit event data
        trigger_config (dict): The trigger configuration
        
    Returns:
        str: The severity level (critical, high, medium, low, info)
    """
    # Get severity from the event details if available
    if 'details' in event_data and 'severity' in event_data['details']:
        return event_data['details']['severity']
    
    # Fall back to trigger configuration
    return trigger_config.get('severity', 'medium')

def generate_alert_content(event_data, trigger_name, severity):
    """
    Generate alert content based on the event data.
    
    Args:
        event_data (dict): The audit event data
        trigger_name (str): The name of the trigger that fired
        severity (str): The alert severity
        
    Returns:
        dict: The alert content with subject and body
    """
    # Get event timestamp and format for display
    timestamp = event_data.get('timestamp', datetime.now(UTC).isoformat())
    if isinstance(timestamp, str):
        # Try to parse the ISO format timestamp
        try:
            timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except ValueError:
            formatted_time = timestamp
    else:
        formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Generate alert subject
    subject = f"[{severity.upper()}] Security Alert: {trigger_name}"
    
    # Generate alert body
    body = f"""
    <h2>Security Alert: {trigger_name}</h2>
    <p><strong>Severity:</strong> {severity.upper()}</p>
    <p><strong>Event Type:</strong> {event_data.get('event_type')}</p>
    <p><strong>Action:</strong> {event_data.get('action')}</p>
    <p><strong>Timestamp:</strong> {formatted_time}</p>
    <p><strong>Actor:</strong> {event_data.get('actor_type', 'Unknown')} (ID: {event_data.get('actor_id', 'Unknown')})</p>
    <p><strong>Outcome:</strong> {event_data.get('outcome', 'Unknown')}</p>
    """
    
    # Add resource info if available
    if event_data.get('resource_id') or event_data.get('resource_type'):
        body += f"""
        <p><strong>Resource:</strong> {event_data.get('resource_type', 'Unknown')} 
        (ID: {event_data.get('resource_id', 'Unknown')})</p>
        """
    
    # Add IP and user agent if available
    if event_data.get('ip_address') or event_data.get('user_agent'):
        body += f"""
        <p><strong>IP Address:</strong> {event_data.get('ip_address', 'Unknown')}</p>
        <p><strong>User Agent:</strong> {event_data.get('user_agent', 'Unknown')}</p>
        """
    
    # Add details if available
    if event_data.get('details'):
        body += "<h3>Event Details:</h3><pre>"
        if isinstance(event_data['details'], dict):
            for key, value in event_data['details'].items():
                body += f"<strong>{key}:</strong> {value}<br>"
        else:
            body += str(event_data['details'])
        body += "</pre>"
    
    # Add link to audit trail
    body += f"""
    <p><a href="{current_app.config.get('DASHBOARD_URL', '#')}/admin/audit/events/{event_data.get('event_id', '')}">
    View in Audit Trail</a></p>
    """
    
    return {
        'subject': subject,
        'body': body
    }

def send_security_alert(event_data, trigger_name, severity):
    """
    Send a security alert notification.
    
    Args:
        event_data (dict): The audit event data
        trigger_name (str): The name of the trigger that fired
        severity (str): The alert severity
        
    Returns:
        bool: Whether the alert was sent successfully
    """
    try:
        # Map severity to priority
        priority = SEVERITY_PRIORITY_MAP.get(severity.lower(), 'normal')
        
        # Skip alerts for info-level events
        if priority is None:
            return True
        
        # Get alert content
        alert_content = generate_alert_content(event_data, trigger_name, severity)
        
        # Get admin recipients from config
        admin_emails = current_app.config.get('SECURITY_ALERT_EMAILS', [])
        if not admin_emails:
            logger.warning("No security alert recipients configured")
            return False
        
        # Prepare notification data
        notification_data = {
            'event_id': event_data.get('event_id'),
            'event_type': event_data.get('event_type'),
            'action': event_data.get('action'),
            'severity': severity,
            'timestamp': event_data.get('timestamp'),
            'actor_id': event_data.get('actor_id'),
            'actor_type': event_data.get('actor_type'),
            'outcome': event_data.get('outcome'),
            'alert_content': alert_content
        }
        
        # Log the alert
        logger.info(f"Sending security alert: {trigger_name} ({severity})")
        
        # Send to each recipient
        for email in admin_emails:
            recipient = {'email': email, 'user_type': 'admin'}
            
            # Use notification queue for async delivery
            if notification_queue.redis_client:
                notification_queue.enqueue(
                    notification_type='security_alert',
                    recipient=recipient,
                    data=notification_data,
                    channel='email', # Could be 'all' for multi-channel
                    priority=priority
                )
            else:
                # Fallback to direct delivery if queue not available
                notification_service.send_notification(
                    notification_type='security_alert',
                    recipient=recipient,
                    data=notification_data,
                    channel='email'
                )
        
        # Also send in-app notification for admins
        if notification_queue.redis_client:
            notification_queue.enqueue(
                notification_type='security_alert',
                recipient={'role': 'admin'},
                data=notification_data,
                channel='in_app',
                priority=priority
            )
        
        # Create an audit event for the alert itself
        audit_security_event(
            event_name="security_alert_sent",
            severity=severity,
            actor_id="system",
            details={
                'trigger_name': trigger_name,
                'event_id': event_data.get('event_id'),
                'recipients': admin_emails
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending security alert: {e}")
        return False

def process_event_for_alerts(event_data):
    """
    Process an audit event and trigger alerts if needed.
    
    Args:
        event_data (dict): The audit event data
        
    Returns:
        bool: Whether any alerts were triggered
    """
    alerts_triggered = False
    
    # Check each trigger configuration
    for trigger_name, trigger_config in ALERT_TRIGGERS.items():
        if is_alert_needed(event_data, trigger_config):
            # Get severity
            severity = get_alert_severity(event_data, trigger_config)
            
            # Send alert
            alert_sent = send_security_alert(event_data, trigger_name, severity)
            
            if alert_sent:
                alerts_triggered = True
                logger.info(f"Security alert triggered: {trigger_name} ({severity})")
    
    return alerts_triggered
