"""
TechSaaS Anomaly Detection API Routes

This module provides API routes for interacting with the anomaly detection system,
including viewing detected anomalies, managing detection settings, and performing
manual reviews.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, current_app, g

from api.v1.utils.anomaly_detection import (
    AnomalyManager, AnomalyEvent, AnomalySeverity, AnomalyType, ResponseAction
)
from api.v1.utils.anomaly_detectors import (
    AccessTimeAnomalyDetector, GeoLocationAnomalyDetector
)
from api.v1.utils.anomaly_detectors_request import (
    RequestFrequencyAnomalyDetector, AuthenticationAnomalyDetector
)
from api.v1.utils.auth_utils import require_auth, require_admin
from api.v1.utils.logging_service import LoggingService

# Create blueprint
anomaly_blueprint = Blueprint('anomaly', __name__)

# Set up logging
logger = logging.getLogger("techsaas.api.anomaly")
logging_service = LoggingService()

# Initialize anomaly manager
anomaly_manager = None

def init_anomaly_manager():
    """Initialize the anomaly detection system"""
    global anomaly_manager
    
    if anomaly_manager is not None:
        return
    
    # Create anomaly manager
    storage_path = os.environ.get("ANOMALY_STORAGE_PATH", "data/anomalies")
    anomaly_manager = AnomalyManager()
    
    # Register detectors
    anomaly_manager.register_detector(AccessTimeAnomalyDetector())
    anomaly_manager.register_detector(GeoLocationAnomalyDetector())
    anomaly_manager.register_detector(RequestFrequencyAnomalyDetector())
    anomaly_manager.register_detector(AuthenticationAnomalyDetector())
    
    # Try to load saved models
    for detector_name, detector in anomaly_manager.detectors.items():
        if hasattr(detector, 'load_model'):
            try:
                detector.load_model(storage_path)
                if detector.baseline_established:
                    logger.info(f"Loaded model for detector {detector_name}")
            except Exception as e:
                logger.warning(f"Failed to load model for detector {detector_name}: {str(e)}")

@anomaly_blueprint.before_request
def before_request():
    """Initialize anomaly manager before handling requests"""
    init_anomaly_manager()

@anomaly_blueprint.route('/anomalies', methods=['GET'])
@require_auth
@require_admin
def get_anomalies():
    """
    Get list of detected anomalies with filtering options
    
    Query parameters:
    - limit: Maximum number of anomalies to return (default: 100)
    - status: Filter by status (new, under_review, resolved, false_positive)
    - severity: Filter by severity (critical, high, medium, low, info)
    - type: Filter by anomaly type
    - from_date: Get anomalies detected after this date (ISO format)
    - to_date: Get anomalies detected before this date (ISO format)
    - user_id: Filter by user ID
    
    Returns:
        JSON array of anomaly events
    """
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 100)), 1000)
        status = request.args.get('status')
        severity_str = request.args.get('severity')
        type_str = request.args.get('type')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        user_id = request.args.get('user_id')
        
        # Convert severity to enum if provided
        severity = None
        if severity_str:
            try:
                severity = [AnomalySeverity(s) for s in severity_str.split(',')]
            except ValueError:
                return jsonify({"error": f"Invalid severity: {severity_str}"}), 400
        
        # Convert type to enum if provided
        anomaly_type = None
        if type_str:
            try:
                anomaly_type = [AnomalyType(t) for t in type_str.split(',')]
            except ValueError:
                return jsonify({"error": f"Invalid anomaly type: {type_str}"}), 400
        
        # Get anomalies
        anomalies = anomaly_manager.get_recent_anomalies(
            limit=limit,
            severity=severity,
            anomaly_type=anomaly_type
        )
        
        # Apply additional filters
        if status or from_date or to_date or user_id:
            filtered_anomalies = []
            
            for anomaly in anomalies:
                # Filter by status
                if status and anomaly.status != status:
                    continue
                
                # Filter by date range
                if from_date:
                    try:
                        anomaly_date = datetime.datetime.fromisoformat(
                            anomaly.timestamp.replace('Z', '+00:00'))
                        from_datetime = datetime.datetime.fromisoformat(
                            from_date.replace('Z', '+00:00'))
                        
                        if anomaly_date < from_datetime:
                            continue
                    except ValueError:
                        pass
                
                if to_date:
                    try:
                        anomaly_date = datetime.datetime.fromisoformat(
                            anomaly.timestamp.replace('Z', '+00:00'))
                        to_datetime = datetime.datetime.fromisoformat(
                            to_date.replace('Z', '+00:00'))
                        
                        if anomaly_date > to_datetime:
                            continue
                    except ValueError:
                        pass
                
                # Filter by user ID
                if user_id and anomaly.user_id != user_id:
                    continue
                
                filtered_anomalies.append(anomaly)
            
            anomalies = filtered_anomalies
        
        # Convert to dictionaries
        result = [anomaly.to_dict() for anomaly in anomalies]
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting anomalies: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/anomalies/<anomaly_id>', methods=['GET'])
@require_auth
@require_admin
def get_anomaly(anomaly_id):
    """
    Get a specific anomaly by ID
    
    Parameters:
        anomaly_id: ID of the anomaly to retrieve
    
    Returns:
        JSON object representing the anomaly
    """
    try:
        anomaly = anomaly_manager.get_anomaly(anomaly_id)
        
        if not anomaly:
            return jsonify({"error": "Anomaly not found"}), 404
        
        return jsonify(anomaly.to_dict())
    except Exception as e:
        logger.error(f"Error getting anomaly {anomaly_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/anomalies/<anomaly_id>/status', methods=['PUT'])
@require_auth
@require_admin
def update_anomaly_status(anomaly_id):
    """
    Update the status of an anomaly
    
    Parameters:
        anomaly_id: ID of the anomaly to update
    
    Request body:
    {
        "status": "new|under_review|resolved|false_positive",
        "comments": "Optional review comments",
    }
    
    Returns:
        JSON success/error response
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        status = data.get('status')
        comments = data.get('comments')
        
        if not status:
            return jsonify({"error": "Missing status"}), 400
        
        if status not in ["new", "under_review", "resolved", "false_positive"]:
            return jsonify({"error": "Invalid status"}), 400
        
        # Get current user ID from auth info
        reviewer_id = g.user_id if hasattr(g, 'user_id') else None
        
        # Update anomaly status
        success = anomaly_manager.update_anomaly_status(
            anomaly_id=anomaly_id,
            status=status,
            review_comments=comments,
            reviewer_id=reviewer_id
        )
        
        if not success:
            return jsonify({"error": "Failed to update anomaly status"}), 500
        
        # Log the action
        logging_service.log_security_event(
            event_type="anomaly_status_updated",
            severity="info",
            user_id=reviewer_id,
            description=f"Anomaly {anomaly_id} status updated to {status}",
            metadata={
                "anomaly_id": anomaly_id,
                "new_status": status,
                "comments": comments
            }
        )
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating anomaly status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/anomalies/dashboard', methods=['GET'])
@require_auth
@require_admin
def get_dashboard_data():
    """
    Get aggregated data for anomaly dashboard
    
    Returns:
        JSON object with dashboard statistics
    """
    try:
        # Get recent anomalies
        anomalies = anomaly_manager.get_recent_anomalies(limit=1000)
        
        # Get counts by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        # Get counts by status
        status_counts = {
            "new": 0,
            "under_review": 0,
            "resolved": 0,
            "false_positive": 0
        }
        
        # Get counts by type
        type_counts = {}
        
        # Get recent anomalies by day (for chart)
        daily_counts = {}
        
        for anomaly in anomalies:
            # Count by severity
            severity = anomaly.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Count by status
            status = anomaly.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by type
            anomaly_type = anomaly.anomaly_type.value
            type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1
            
            # Count by day
            try:
                date_str = anomaly.timestamp.split('T')[0]  # YYYY-MM-DD
                daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
            except Exception:
                pass
        
        # Get top affected users
        user_counts = {}
        for anomaly in anomalies:
            if anomaly.user_id:
                user_counts[anomaly.user_id] = user_counts.get(anomaly.user_id, 0) + 1
        
        top_users = [
            {"user_id": user_id, "count": count}
            for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Get top source IPs
        ip_counts = {}
        for anomaly in anomalies:
            if anomaly.source_ip:
                ip_counts[anomaly.source_ip] = ip_counts.get(anomaly.source_ip, 0) + 1
        
        top_ips = [
            {"ip": ip, "count": count}
            for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Prepare chart data (last 30 days)
        today = datetime.date.today()
        chart_data = []
        
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            date_str = date.isoformat()
            chart_data.append({
                "date": date_str,
                "count": daily_counts.get(date_str, 0)
            })
        
        chart_data.reverse()  # Oldest to newest
        
        # Prepare response
        result = {
            "counts": {
                "total": len(anomalies),
                "by_severity": severity_counts,
                "by_status": status_counts,
                "by_type": type_counts
            },
            "top_users": top_users,
            "top_ips": top_ips,
            "chart_data": chart_data
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/anomalies/cleanup', methods=['POST'])
@require_auth
@require_admin
def cleanup_old_anomalies():
    """
    Clean up old anomaly records
    
    Returns:
        JSON success/error response with count of removed anomalies
    """
    try:
        # Run cleanup
        removed_count = anomaly_manager.cleanup_old_anomalies()
        
        # Log the action
        reviewer_id = g.user_id if hasattr(g, 'user_id') else None
        logging_service.log_security_event(
            event_type="anomaly_cleanup",
            severity="info",
            user_id=reviewer_id,
            description=f"Cleaned up {removed_count} old anomaly records",
            metadata={
                "removed_count": removed_count
            }
        )
        
        return jsonify({
            "success": True,
            "removed_count": removed_count
        })
    except Exception as e:
        logger.error(f"Error cleaning up anomalies: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/settings', methods=['GET'])
@require_auth
@require_admin
def get_detector_settings():
    """
    Get current settings for all anomaly detectors
    
    Returns:
        JSON object with detector settings
    """
    try:
        # Get settings for each detector
        settings = {}
        
        for name, detector in anomaly_manager.detectors.items():
            detector_settings = {
                "name": name,
                "type": detector.anomaly_type.value,
                "enabled": detector.enabled,
                "baseline_established": detector.baseline_established
            }
            
            if detector.last_training_time:
                detector_settings["last_training_time"] = detector.last_training_time
            
            # Add any detector-specific settings
            if name == "access_time_detector" and hasattr(detector, "z_score_threshold"):
                detector_settings["z_score_threshold"] = detector.z_score_threshold
            
            settings[name] = detector_settings
        
        # Add general settings
        result = {
            "detectors": settings,
            "general": {
                "storage_path": anomaly_manager.storage_path,
                "detection_threshold": anomaly_manager.config.get("detection_threshold", 0.8),
                "enable_responses": anomaly_manager.config.get("enable_responses", True),
                "storage_retention_days": anomaly_manager.config.get("storage_retention_days", 30)
            }
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting detector settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/settings', methods=['PUT'])
@require_auth
@require_admin
def update_detector_settings():
    """
    Update settings for anomaly detectors
    
    Request body:
    {
        "general": {
            "detection_threshold": 0.8,
            "enable_responses": true,
            "storage_retention_days": 30
        },
        "detectors": {
            "detector_name": {
                "enabled": true
            }
        }
    }
    
    Returns:
        JSON success/error response
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        # Update general settings
        if "general" in data:
            general = data["general"]
            
            if "detection_threshold" in general:
                anomaly_manager.config["detection_threshold"] = float(general["detection_threshold"])
            
            if "enable_responses" in general:
                anomaly_manager.config["enable_responses"] = bool(general["enable_responses"])
            
            if "storage_retention_days" in general:
                anomaly_manager.config["storage_retention_days"] = int(general["storage_retention_days"])
        
        # Update detector settings
        if "detectors" in data:
            detector_settings = data["detectors"]
            
            for name, settings in detector_settings.items():
                if name in anomaly_manager.detectors:
                    detector = anomaly_manager.detectors[name]
                    
                    if "enabled" in settings:
                        detector.enabled = bool(settings["enabled"])
                    
                    # Update detector-specific settings
                    if name == "access_time_detector" and "z_score_threshold" in settings:
                        detector.z_score_threshold = float(settings["z_score_threshold"])
        
        # Log the action
        reviewer_id = g.user_id if hasattr(g, 'user_id') else None
        logging_service.log_security_event(
            event_type="anomaly_settings_updated",
            severity="info",
            user_id=reviewer_id,
            description="Anomaly detection settings updated",
            metadata={
                "updated_settings": data
            }
        )
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating detector settings: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@anomaly_blueprint.route('/train', methods=['POST'])
@require_auth
@require_admin
def train_detectors():
    """
    Train anomaly detectors with historical data
    
    Request body:
    {
        "detectors": ["detector_name1", "detector_name2"] or null for all,
        "max_events": 10000
    }
    
    Returns:
        JSON success/error response with training results
    """
    try:
        # Get request data
        data = request.get_json() or {}
        
        detector_names = data.get('detectors')
        max_events = int(data.get('max_events', 10000))
        
        # Get training data from logs
        # In a real implementation, you would query your logging database
        # For demonstration purposes, we'll generate mock training data
        training_data = _generate_mock_training_data(max_events)
        
        # Train specific detectors or all
        results = {}
        
        for name, detector in anomaly_manager.detectors.items():
            if detector_names is None or name in detector_names:
                try:
                    success = detector.train(training_data)
                    results[name] = {
                        "success": success,
                        "baseline_established": detector.baseline_established
                    }
                    
                    # Save the model
                    if success and hasattr(detector, 'save_model'):
                        detector.save_model(anomaly_manager.storage_path)
                except Exception as e:
                    logger.error(f"Error training detector {name}: {str(e)}")
                    results[name] = {
                        "success": False,
                        "error": str(e)
                    }
        
        # Log the action
        reviewer_id = g.user_id if hasattr(g, 'user_id') else None
        logging_service.log_security_event(
            event_type="anomaly_detectors_trained",
            severity="info",
            user_id=reviewer_id,
            description="Anomaly detectors trained",
            metadata={
                "results": results,
                "training_events": len(training_data)
            }
        )
        
        return jsonify({
            "success": True,
            "results": results,
            "training_events": len(training_data)
        })
    except Exception as e:
        logger.error(f"Error training detectors: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def _generate_mock_training_data(count):
    """Generate mock training data for demonstration purposes"""
    import random
    from datetime import datetime, timedelta
    
    data = []
    users = [f"user{i}" for i in range(1, 11)]
    ips = [f"192.168.1.{i}" for i in range(1, 101)]
    endpoints = [
        "/api/v1/users",
        "/api/v1/auth/login",
        "/api/v1/products",
        "/api/v1/orders",
        "/api/v1/dashboard"
    ]
    
    now = datetime.now()
    
    for i in range(count):
        # Generate event with random timestamp in the past 30 days
        random_days = random.randint(0, 30)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        timestamp = now - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        user_id = random.choice(users)
        ip_address = random.choice(ips)
        endpoint = random.choice(endpoints)
        
        # Generate event
        event = {
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "authentication_success": random.random() > 0.1  # 10% failure rate
        }
        
        data.append(event)
    
    return data

# Register blueprint with app
def init_app(app):
    """Initialize the anomaly detection routes with the Flask app"""
    app.register_blueprint(anomaly_blueprint, url_prefix='/api/v1/security')
    logger.info("Registered anomaly detection routes")
