#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security Incident Response API Routes

This module provides API endpoints for managing security incidents,
including creation, updating, and retrieval of incidents.

Author: TechSaaS Security Team
Date: May 4, 2025
"""

from flask import Blueprint, request, jsonify, current_app, g
import datetime
import json
from typing import Dict, List, Optional

from ..utils.incident_response import (
    IncidentManager,
    IncidentSeverity,
    IncidentStatus,
    IncidentType
)
from ..utils.anomaly_detection import AnomalyManager
from ..middleware.authentication import auth_required, admin_required
from ..services.logging_service import LoggingService


# Create blueprint for incident response routes
incident_blueprint = Blueprint('incident_response', __name__)
logger = LoggingService("incident_api")


# Initialize the incident manager
incident_manager = IncidentManager()


@incident_blueprint.route('/api/v1/security/incidents', methods=['GET'])
@auth_required
@admin_required
def list_incidents():
    """
    List security incidents with optional filtering.
    
    Query Parameters:
        status: Filter by incident status
        severity: Filter by severity level
        type: Filter by incident type
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        sort_by: Field to sort by (default: created_at)
        sort_order: Sort direction (asc or desc, default: desc)
        
    Returns:
        List of incidents matching the filter criteria
    """
    try:
        # Parse query parameters
        filters = {}
        
        status = request.args.get('status')
        if status:
            filters['status'] = status
            
        severity = request.args.get('severity')
        if severity:
            filters['severity'] = severity
            
        incident_type = request.args.get('type')
        if incident_type:
            filters['incident_type'] = incident_type
            
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            filters['time_range'] = {
                'start': start_date,
                'end': end_date
            }
            
        # Parse sorting parameters
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get incidents matching filters
        incidents = incident_manager.list_incidents(filters, sort_by, sort_order)
        
        # Log the request
        logger.info(f"Listed {len(incidents)} incidents with filters: {filters}")
        
        return jsonify({
            'status': 'success',
            'count': len(incidents),
            'incidents': incidents
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing incidents: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to list incidents: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>', methods=['GET'])
@auth_required
@admin_required
def get_incident(incident_id):
    """
    Get details of a specific security incident.
    
    Path Parameters:
        incident_id: ID of the incident to retrieve
        
    Returns:
        Complete incident details
    """
    try:
        incident = incident_manager.get_incident(incident_id)
        
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
            
        # Log the access
        logger.info(f"Retrieved incident {incident_id}")
        
        return jsonify({
            'status': 'success',
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to retrieve incident: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/status', methods=['PUT'])
@auth_required
@admin_required
def update_incident_status(incident_id):
    """
    Update the status of a security incident.
    
    Path Parameters:
        incident_id: ID of the incident to update
        
    JSON Body:
        status: New incident status
        notes: Optional notes about the status change
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        if not data or 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': "Status field is required"
            }), 400
            
        # Validate status value
        try:
            new_status = data['status']
            # Ensure the status is valid
            IncidentStatus(new_status)
        except ValueError:
            valid_statuses = [status.value for status in IncidentStatus]
            return jsonify({
                'status': 'error',
                'message': f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400
        
        # Update the incident
        notes = data.get('notes')
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        incident = incident_manager.update_incident(
            incident_id=incident_id,
            updates={'status': new_status},
            user_id=user_id
        )
        
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Add notes as an event if provided
        if notes:
            incident_manager.add_incident_event(
                incident_id=incident_id,
                event_type='status_note',
                description=notes,
                user_id=user_id
            )
        
        # Log the status update
        logger.info(f"Updated incident {incident_id} status to {new_status}")
        
        return jsonify({
            'status': 'success',
            'message': f"Incident status updated to {new_status}",
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to update incident: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/assign', methods=['PUT'])
@auth_required
@admin_required
def assign_incident(incident_id):
    """
    Assign a security incident to a team member.
    
    Path Parameters:
        incident_id: ID of the incident to assign
        
    JSON Body:
        assignee_id: ID of the user to assign the incident to
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        if not data or 'assignee_id' not in data:
            return jsonify({
                'status': 'error',
                'message': "assignee_id field is required"
            }), 400
            
        assignee_id = data['assignee_id']
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        # Update the incident
        incident = incident_manager.update_incident(
            incident_id=incident_id,
            updates={'assigned_to': assignee_id},
            user_id=user_id
        )
        
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Add assignment event
        incident_manager.add_incident_event(
            incident_id=incident_id,
            event_type='assignment',
            description=f"Assigned to {assignee_id}",
            user_id=user_id,
            details={'assignee_id': assignee_id}
        )
        
        # Log the assignment
        logger.info(f"Assigned incident {incident_id} to {assignee_id}")
        
        return jsonify({
            'status': 'success',
            'message': f"Incident assigned to {assignee_id}",
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to assign incident: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/events', methods=['POST'])
@auth_required
@admin_required
def add_incident_event(incident_id):
    """
    Add an event to an incident timeline.
    
    Path Parameters:
        incident_id: ID of the incident
        
    JSON Body:
        event_type: Type of event
        description: Description of what occurred
        details: Additional details about the event (optional)
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        if not data or 'event_type' not in data or 'description' not in data:
            return jsonify({
                'status': 'error',
                'message': "event_type and description fields are required"
            }), 400
            
        event_type = data['event_type']
        description = data['description']
        details = data.get('details')
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        # Add the event
        incident = incident_manager.add_incident_event(
            incident_id=incident_id,
            event_type=event_type,
            description=description,
            user_id=user_id,
            details=details
        )
        
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Log the event addition
        logger.info(f"Added {event_type} event to incident {incident_id}")
        
        return jsonify({
            'status': 'success',
            'message': f"Event added to incident timeline",
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding event to incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to add event: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/containment', methods=['POST'])
@auth_required
@admin_required
def add_containment_action(incident_id):
    """
    Add a containment action to an incident.
    
    Path Parameters:
        incident_id: ID of the incident
        
    JSON Body:
        action_type: Type of containment action
        description: Description of the action
        details: Additional details about the action (optional)
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        if not data or 'action_type' not in data or 'description' not in data:
            return jsonify({
                'status': 'error',
                'message': "action_type and description fields are required"
            }), 400
            
        action_type = data['action_type']
        description = data['description']
        details = data.get('details')
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        # Get the incident
        incident = incident_manager.get_incident(incident_id)
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Add containment action
        if 'containment_actions' not in incident:
            incident['containment_actions'] = []
            
        action = {
            "action_id": str(datetime.datetime.now().timestamp()),
            "action_type": action_type,
            "description": description,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "user_id": user_id,
            "details": details or {}
        }
        
        incident['containment_actions'].append(action)
        incident['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save the incident
        incident_manager.save_incident(incident)
        
        # Add corresponding event
        incident_manager.add_incident_event(
            incident_id=incident_id,
            event_type='containment_action',
            description=f"Containment action initiated: {description}",
            user_id=user_id,
            details={"action_id": action["action_id"]}
        )
        
        # Log the containment action
        logger.info(f"Added containment action to incident {incident_id}: {description}")
        
        return jsonify({
            'status': 'success',
            'message': f"Containment action added",
            'action': action,
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding containment action to incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to add containment action: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/containment/<action_id>', methods=['PUT'])
@auth_required
@admin_required
def update_containment_action(incident_id, action_id):
    """
    Update the status of a containment action.
    
    Path Parameters:
        incident_id: ID of the incident
        action_id: ID of the containment action
        
    JSON Body:
        status: New status of the action
        notes: Optional notes about the status update
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        if not data or 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': "status field is required"
            }), 400
            
        status = data['status']
        notes = data.get('notes')
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        # Get the incident
        incident = incident_manager.get_incident(incident_id)
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Find and update the containment action
        action_updated = False
        if 'containment_actions' in incident:
            for action in incident['containment_actions']:
                if action.get('action_id') == action_id:
                    old_status = action.get('status')
                    action['status'] = status
                    action['updated_at'] = datetime.datetime.now().isoformat()
                    
                    if notes:
                        action['notes'] = notes
                        
                    action_updated = True
                    break
        
        if not action_updated:
            return jsonify({
                'status': 'error',
                'message': f"Containment action {action_id} not found in incident {incident_id}"
            }), 404
        
        # Update the incident
        incident['updated_at'] = datetime.datetime.now().isoformat()
        incident_manager.save_incident(incident)
        
        # Add corresponding event
        incident_manager.add_incident_event(
            incident_id=incident_id,
            event_type='containment_update',
            description=f"Containment action status changed from {old_status} to {status}",
            user_id=user_id,
            details={
                "action_id": action_id,
                "old_status": old_status,
                "new_status": status,
                "notes": notes
            }
        )
        
        # Log the update
        logger.info(f"Updated containment action {action_id} status to {status} for incident {incident_id}")
        
        return jsonify({
            'status': 'success',
            'message': f"Containment action status updated to {status}",
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating containment action {action_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to update containment action: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/<incident_id>/evidence', methods=['POST'])
@auth_required
@admin_required
def add_evidence(incident_id):
    """
    Add evidence to an incident investigation.
    
    Path Parameters:
        incident_id: ID of the incident
        
    JSON Body:
        evidence_type: Type of evidence
        description: Description of the evidence
        location: Where the evidence is stored
        metadata: Additional metadata about the evidence (optional)
        
    Returns:
        Updated incident details
    """
    try:
        data = request.json
        
        required_fields = ['evidence_type', 'description', 'location']
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': f"Required fields: {', '.join(required_fields)}"
            }), 400
            
        evidence_type = data['evidence_type']
        description = data['description']
        location = data['location']
        metadata = data.get('metadata')
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        # Get the incident
        incident = incident_manager.get_incident(incident_id)
        if not incident:
            return jsonify({
                'status': 'error',
                'message': f"Incident {incident_id} not found"
            }), 404
        
        # Add evidence
        if 'evidence_list' not in incident:
            incident['evidence_list'] = []
            
        evidence = {
            "evidence_id": str(datetime.datetime.now().timestamp()),
            "evidence_type": evidence_type,
            "description": description,
            "location": location,
            "collected_at": datetime.datetime.now().isoformat(),
            "collector_id": user_id,
            "chain_of_custody": [{
                "timestamp": datetime.datetime.now().isoformat(),
                "action": "collected",
                "user_id": user_id,
                "notes": "Initial collection"
            }],
            "metadata": metadata or {}
        }
        
        incident['evidence_list'].append(evidence)
        incident['updated_at'] = datetime.datetime.now().isoformat()
        
        # Save the incident
        incident_manager.save_incident(incident)
        
        # Add corresponding event
        incident_manager.add_incident_event(
            incident_id=incident_id,
            event_type='evidence_collection',
            description=f"Evidence collected: {description}",
            user_id=user_id,
            details={"evidence_id": evidence["evidence_id"]}
        )
        
        # Log the evidence addition
        logger.info(f"Added evidence to incident {incident_id}: {description}")
        
        return jsonify({
            'status': 'success',
            'message': f"Evidence added to incident",
            'evidence': evidence,
            'incident': incident
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding evidence to incident {incident_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to add evidence: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/stats', methods=['GET'])
@auth_required
@admin_required
def get_incident_statistics():
    """
    Get statistics about security incidents.
    
    Query Parameters:
        start_date: Start date for statistics (ISO format)
        end_date: End date for statistics (ISO format)
        
    Returns:
        Incident statistics
    """
    try:
        # Parse date range
        start_date = request.args.get('start_date', 
                                      (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat())
        end_date = request.args.get('end_date', datetime.datetime.now().isoformat())
        
        # Get incidents in the date range
        incidents = incident_manager.list_incidents(
            filters={'time_range': {'start': start_date, 'end': end_date}},
            sort_by='created_at',
            sort_order='asc'
        )
        
        # Calculate statistics
        total_incidents = len(incidents)
        
        # Count by severity
        severity_counts = {}
        for severity in [s.name for s in IncidentSeverity]:
            severity_counts[severity] = sum(1 for i in incidents if i.get('severity') == severity)
            
        # Count by status
        status_counts = {}
        for status in [s.value for s in IncidentStatus]:
            status_counts[status] = sum(1 for i in incidents if i.get('status') == status)
            
        # Count by type
        type_counts = {}
        for inc_type in [t.name for t in IncidentType]:
            type_counts[inc_type] = sum(1 for i in incidents if i.get('incident_type') == inc_type)
            
        # Calculate average time to resolution
        resolved_incidents = [i for i in incidents if i.get('status') == IncidentStatus.RESOLVED.value]
        avg_resolution_time = None
        
        if resolved_incidents:
            resolution_times = []
            
            for incident in resolved_incidents:
                created_at = datetime.datetime.fromisoformat(incident['created_at'])
                
                # Find the resolution event
                resolution_event = None
                for event in incident.get('events', []):
                    if (event.get('event_type') == 'status_change' and 
                        event.get('details', {}).get('new_status') == IncidentStatus.RESOLVED.value):
                        resolution_event = event
                        break
                
                if resolution_event:
                    resolved_at = datetime.datetime.fromisoformat(resolution_event['timestamp'])
                    resolution_time = (resolved_at - created_at).total_seconds() / 3600  # in hours
                    resolution_times.append(resolution_time)
            
            if resolution_times:
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        # Format the statistics
        statistics = {
            'total_incidents': total_incidents,
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'by_severity': severity_counts,
            'by_status': status_counts,
            'by_type': type_counts,
            'avg_resolution_time_hours': avg_resolution_time
        }
        
        # Log the access
        logger.info(f"Retrieved incident statistics for period {start_date} to {end_date}")
        
        return jsonify({
            'status': 'success',
            'statistics': statistics
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving incident statistics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to retrieve statistics: {str(e)}"
        }), 500


@incident_blueprint.route('/api/v1/security/incidents/create-from-anomaly', methods=['POST'])
@auth_required
@admin_required
def create_incident_from_anomaly():
    """
    Create a new incident from an anomaly event.
    
    JSON Body:
        anomaly_id: ID of the anomaly to create an incident from
        additional_info: Additional information to include in the incident (optional)
        
    Returns:
        The created incident details
    """
    try:
        data = request.json
        
        if not data or 'anomaly_id' not in data:
            return jsonify({
                'status': 'error',
                'message': "anomaly_id field is required"
            }), 400
            
        anomaly_id = data['anomaly_id']
        additional_info = data.get('additional_info', {})
        
        # Get the anomaly
        anomaly_manager = AnomalyManager()
        anomaly = anomaly_manager.get_anomaly(anomaly_id)
        
        if not anomaly:
            return jsonify({
                'status': 'error',
                'message': f"Anomaly {anomaly_id} not found"
            }), 404
        
        # Create incident
        incident = incident_manager.create_incident_from_anomaly(anomaly, additional_info)
        
        # Log the creation
        logger.info(f"Created incident {incident.incident_id} from anomaly {anomaly_id}")
        
        return jsonify({
            'status': 'success',
            'message': f"Incident created from anomaly",
            'incident': incident.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating incident from anomaly: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to create incident: {str(e)}"
        }), 500


# Register this blueprint with the Flask application
def register_incident_routes(app):
    app.register_blueprint(incident_blueprint)
