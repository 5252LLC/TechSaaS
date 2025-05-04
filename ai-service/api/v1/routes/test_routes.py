"""
Test Routes for Security Testing

This module provides endpoints that are specifically designed to test
security features like authentication and authorization. These routes
should only be enabled in test environments.
"""

from flask import Blueprint, jsonify, g
from ..middleware.authorization import jwt_required, has_permission, role_required, tier_required
from ..utils.response_formatter import ResponseFormatter

test_bp = Blueprint('test', __name__)

# Public routes (no authentication required)
@test_bp.route('/api/v1/status')
def status():
    """Public endpoint for status check"""
    return ResponseFormatter.success_response(
        message="API is operational",
        data={"status": "healthy"}
    )

@test_bp.route('/api/v1/docs')
def docs():
    """Public endpoint for API documentation"""
    return ResponseFormatter.success_response(
        message="API documentation",
        data={"documentation": "URL to API documentation"}
    )

# User routes (basic authentication required)
@test_bp.route('/api/v1/protected/user-profile')
@jwt_required
def user_profile():
    """Protected endpoint for user profile - requires authentication"""
    return ResponseFormatter.success_response(
        message="User profile accessed",
        data={"user_id": g.user.get('sub')}
    )

@test_bp.route('/api/v1/protected/dashboard')
@jwt_required
def user_dashboard():
    """Protected endpoint for user dashboard - requires authentication"""
    return ResponseFormatter.success_response(
        message="User dashboard accessed",
        data={"user_id": g.user.get('sub')}
    )

# Premium routes (premium tier or higher required)
@test_bp.route('/api/v1/premium/features')
@jwt_required
@tier_required('premium')
def premium_features():
    """Premium endpoint - requires premium tier"""
    return ResponseFormatter.success_response(
        message="Premium features accessed",
        data={"tier": g.user.get('tier')}
    )

@test_bp.route('/api/v1/premium/reports')
@jwt_required
@tier_required('premium')
def premium_reports():
    """Premium endpoint - requires premium tier"""
    return ResponseFormatter.success_response(
        message="Premium reports accessed",
        data={"tier": g.user.get('tier')}
    )

# Admin routes (admin role required)
@test_bp.route('/api/v1/admin/dashboard')
@jwt_required
@role_required('admin')
def admin_dashboard():
    """Admin endpoint - requires admin role"""
    return ResponseFormatter.success_response(
        message="Admin dashboard accessed",
        data={"role": g.user.get('role')}
    )

@test_bp.route('/api/v1/admin/users')
@jwt_required
@role_required('admin')
def admin_users():
    """Admin endpoint - requires admin role"""
    return ResponseFormatter.success_response(
        message="Admin users list accessed",
        data={"role": g.user.get('role')}
    )

@test_bp.route('/api/v1/admin/settings')
@jwt_required
@role_required('admin')
@has_permission('admin:edit')
def admin_settings():
    """Admin endpoint - requires admin role with edit permissions"""
    return ResponseFormatter.success_response(
        message="Admin settings accessed",
        data={"role": g.user.get('role')}
    )
