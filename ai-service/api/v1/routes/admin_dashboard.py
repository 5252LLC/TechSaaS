"""
Admin Dashboard Routes

This module provides routes for the admin dashboard, particularly focusing
on audit trail analytics and visualizations.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta

from api.v1.middleware.admin_required import admin_required
from api.v1.utils.audit_trail import get_audit_trail
from api.v1.routes.anomaly_detection import anomaly_manager, init_anomaly_manager

# Create blueprint
admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/api/v1/admin/dashboard')

@admin_dashboard_bp.route('/')
@jwt_required
@admin_required
def dashboard_home():
    """Render the main admin dashboard page"""
    return render_template('admin/dashboard.html')

@admin_dashboard_bp.route('/audit/stats')
@jwt_required
@admin_required
def audit_stats():
    """Get audit trail statistics for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get statistics
    stats = audit_trail.storage.get_stats(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )
    
    return jsonify(stats)

@admin_dashboard_bp.route('/audit/daily-activity')
@jwt_required
@admin_required
def audit_daily_activity():
    """Get daily audit event counts for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get daily statistics
    daily_stats = audit_trail.storage.get_daily_activity(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )
    
    return jsonify(daily_stats)

@admin_dashboard_bp.route('/audit/event-types')
@jwt_required
@admin_required
def audit_event_types():
    """Get distribution of event types for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get event type distribution
    event_types = audit_trail.storage.get_event_type_distribution(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )
    
    return jsonify(event_types)

@admin_dashboard_bp.route('/audit/outcomes')
@jwt_required
@admin_required
def audit_outcomes():
    """Get distribution of event outcomes for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get outcome distribution
    outcomes = audit_trail.storage.get_outcome_distribution(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )
    
    return jsonify(outcomes)

@admin_dashboard_bp.route('/audit/sensitivity')
@jwt_required
@admin_required
def audit_sensitivity():
    """Get distribution of event sensitivity levels for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get sensitivity distribution
    sensitivity = audit_trail.storage.get_sensitivity_distribution(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )
    
    return jsonify(sensitivity)

@admin_dashboard_bp.route('/audit/top-actors')
@jwt_required
@admin_required
def audit_top_actors():
    """Get top actors in the audit trail for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    limit = int(request.args.get('limit', 10))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get top actors
    top_actors = audit_trail.storage.get_top_actors(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        limit=limit
    )
    
    return jsonify(top_actors)

@admin_dashboard_bp.route('/audit/top-resources')
@jwt_required
@admin_required
def audit_top_resources():
    """Get top resources in the audit trail for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    limit = int(request.args.get('limit', 10))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get top resources
    top_resources = audit_trail.storage.get_top_resources(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        limit=limit
    )
    
    return jsonify(top_resources)

@admin_dashboard_bp.route('/audit/recent-critical-events')
@jwt_required
@admin_required
def audit_recent_critical_events():
    """Get recent critical events for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 7))
    limit = int(request.args.get('limit', 10))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get critical events
    results = audit_trail.search_events(
        query={"sensitivity": "critical"},
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        page=1,
        page_size=limit
    )
    
    return jsonify(results)

@admin_dashboard_bp.route('/audit/security-events')
@jwt_required
@admin_required
def audit_security_events():
    """Get security events for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get security events
    results = audit_trail.search_events(
        query={"event_type": "security_event"},
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        page=1,
        page_size=100
    )
    
    # Analyze security events
    security_analysis = {
        "total_events": len(results.get("results", [])),
        "by_severity": {},
        "by_outcome": {},
        "timeline": {}
    }
    
    for event in results.get("results", []):
        # Count by severity
        severity = event.get("sensitivity", "unknown")
        security_analysis["by_severity"][severity] = security_analysis["by_severity"].get(severity, 0) + 1
        
        # Count by outcome
        outcome = event.get("outcome", "unknown")
        security_analysis["by_outcome"][outcome] = security_analysis["by_outcome"].get(outcome, 0) + 1
        
        # Timeline data (by day)
        try:
            timestamp = event.get("timestamp", "")
            if timestamp:
                date = timestamp.split("T")[0]
                security_analysis["timeline"][date] = security_analysis["timeline"].get(date, 0) + 1
        except (ValueError, IndexError, AttributeError):
            pass
    
    return jsonify(security_analysis)

@admin_dashboard_bp.route('/audit/api-key-events')
@jwt_required
@admin_required
def audit_api_key_events():
    """Get API key related events for the dashboard"""
    # Get query parameters
    days = int(request.args.get('days', 30))
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    # Get audit trail
    audit_trail = get_audit_trail()
    
    # Get API key events
    results = audit_trail.search_events(
        query={"event_type": "api_key_management"},
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        page=1,
        page_size=100
    )
    
    # Analyze API key events
    api_key_analysis = {
        "total_events": len(results.get("results", [])),
        "by_action": {},
        "by_outcome": {},
        "timeline": {}
    }
    
    for event in results.get("results", []):
        # Count by action
        action = event.get("action", "unknown")
        api_key_analysis["by_action"][action] = api_key_analysis["by_action"].get(action, 0) + 1
        
        # Count by outcome
        outcome = event.get("outcome", "unknown")
        api_key_analysis["by_outcome"][outcome] = api_key_analysis["by_outcome"].get(outcome, 0) + 1
        
        # Timeline data (by day)
        try:
            timestamp = event.get("timestamp", "")
            if timestamp:
                date = timestamp.split("T")[0]
                api_key_analysis["timeline"][date] = api_key_analysis["timeline"].get(date, 0) + 1
        except (ValueError, IndexError, AttributeError):
            pass
    
    return jsonify(api_key_analysis)

@admin_dashboard_bp.route('/security/anomalies')
@jwt_required
@admin_required
def security_anomalies_dashboard():
    """Render the security anomalies dashboard page"""
    return render_template('admin/anomaly_dashboard.html')

@admin_dashboard_bp.route('/security/anomalies-summary')
@jwt_required
@admin_required
def security_anomalies_summary():
    """Get a summary of security anomalies for the main dashboard"""
    # Make sure anomaly manager is initialized
    init_anomaly_manager()
    
    # Get recent anomalies (last 30 days)
    severity_filter = [
        "critical",
        "high"
    ]
    
    # Convert to proper enum values
    from api.v1.utils.anomaly_detection import AnomalySeverity
    severity_enum = [AnomalySeverity(s) for s in severity_filter]
    
    # Get high severity anomalies
    high_severity_anomalies = anomaly_manager.get_recent_anomalies(
        limit=100,
        severity=severity_enum
    )
    
    # Get stats
    total_high_severity = len(high_severity_anomalies)
    
    # Get unresolved count
    unresolved = [a for a in high_severity_anomalies if a.status == "new"]
    total_unresolved = len(unresolved)
    
    # Get newest anomaly timestamp
    newest_timestamp = None
    if high_severity_anomalies:
        # Sort by timestamp (newest first)
        sorted_anomalies = sorted(
            high_severity_anomalies,
            key=lambda a: a.timestamp,
            reverse=True
        )
        newest_timestamp = sorted_anomalies[0].timestamp
    
    return jsonify({
        "high_severity_count": total_high_severity,
        "unresolved_count": total_unresolved,
        "newest_timestamp": newest_timestamp
    })

def register_routes(app):
    """Register admin dashboard routes with the Flask application."""
    app.register_blueprint(admin_dashboard_bp)
