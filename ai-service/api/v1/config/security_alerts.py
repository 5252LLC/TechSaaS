"""
Security Alerts Configuration

This module contains configuration settings for the security alerts system.
"""

# Default security alert configuration
DEFAULT_CONFIG = {
    # Enable/disable security alerts
    'SECURITY_ALERTS_ENABLED': True,
    
    # Email addresses to receive security alerts
    'SECURITY_ALERT_EMAILS': ['admin@techsaas.tech', 'security@techsaas.tech'],
    
    # SMS numbers to receive critical alerts (if SMS notifications are configured)
    'SECURITY_ALERT_SMS': [],
    
    # Minimum severity level to trigger alerts
    # Options: 'critical', 'high', 'medium', 'low', 'info'
    'SECURITY_ALERT_MIN_SEVERITY': 'medium',
    
    # Whether to aggregate similar alerts within a time window
    'SECURITY_ALERT_AGGREGATION_ENABLED': True,
    
    # Time window (minutes) for alert aggregation
    'SECURITY_ALERT_AGGREGATION_WINDOW': 10,
    
    # Dashboard URL for admin panel
    'SECURITY_ALERT_DASHBOARD_URL': '/admin/security/alerts',
    
    # Rate limiting to prevent alert storms
    'SECURITY_ALERT_RATE_LIMIT': 10,  # Max alerts per minute
    
    # Whether to include full event details in alerts
    'SECURITY_ALERT_INCLUDE_DETAILS': True
}

def init_app(app):
    """
    Initialize security alerts configuration with app context.
    
    Args:
        app: Flask app
    """
    # Set default config values
    for key, value in DEFAULT_CONFIG.items():
        if key not in app.config:
            app.config[key] = value
            
    # Add security alert emails from environment variable if set
    if app.config.get('SECURITY_ALERT_EMAILS_CSV'):
        emails = app.config['SECURITY_ALERT_EMAILS_CSV'].split(',')
        app.config['SECURITY_ALERT_EMAILS'] = [email.strip() for email in emails]
        
    # Ensure DASHBOARD_URL is set for alert links
    if not app.config.get('DASHBOARD_URL'):
        app.config['DASHBOARD_URL'] = 'https://techsaas.tech/dashboard'
