"""
Usage Endpoints

API routes for monitoring usage, retrieving usage statistics, and generating billing reports.
These endpoints are protected and only accessible to administrators and users viewing their own data.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import logging

from ..middleware.security import jwt_required
from ..middleware.authorization import admin_required, has_permission
from ..utils.response_formatter import format_response
from ..utils.usage_tracker import usage_tracker

# Setup logger
logger = logging.getLogger(__name__)

# Blueprint definition
usage_bp = Blueprint('usage', __name__, url_prefix='/usage')


@usage_bp.route('/summary', methods=['GET'])
@jwt_required
def get_usage_summary():
    """
    Get usage summary for the authenticated user
    
    Query parameters:
        days (int): Number of days to include in summary (default: 30)
    
    Returns:
        JSON: Usage summary data
    """
    # Get user ID from JWT token
    user_id = g.current_user.get('sub')
    
    # Get days parameter
    try:
        days = int(request.args.get('days', 30))
        # Limit to reasonable range
        days = min(max(1, days), 90)
    except ValueError:
        days = 30
    
    # Get usage summary
    summary = usage_tracker.get_usage_summary(user_id, days)
    
    return format_response(
        data=summary,
        message=f"Usage summary for the last {days} days",
        metadata={
            "period": f"Last {days} days",
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/admin/user/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def admin_get_user_usage(user_id):
    """
    Get usage summary for a specific user (admin only)
    
    Path parameters:
        user_id (str): User ID to get usage for
    
    Query parameters:
        days (int): Number of days to include in summary (default: 30)
    
    Returns:
        JSON: Usage summary data for the specified user
    """
    # Get days parameter
    try:
        days = int(request.args.get('days', 30))
        # Limit to reasonable range
        days = min(max(1, days), 90)
    except ValueError:
        days = 30
    
    # Get usage summary
    summary = usage_tracker.get_usage_summary(user_id, days)
    
    return format_response(
        data=summary,
        message=f"Usage summary for user {user_id} over the last {days} days",
        metadata={
            "period": f"Last {days} days",
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/billing', methods=['GET'])
@jwt_required
def get_billing_data():
    """
    Get billing data for the authenticated user
    
    Query parameters:
        start_date (str): Start date in YYYY-MM-DD format (default: first day of current month)
        end_date (str): End date in YYYY-MM-DD format (default: today)
    
    Returns:
        JSON: Billing data for the specified period
    """
    # Get user ID from JWT token
    user_id = g.current_user.get('sub')
    
    # Get date parameters
    today = datetime.utcnow().date()
    first_day = today.replace(day=1)
    
    # Parse dates from query parameters
    try:
        start_date = request.args.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = first_day
    except ValueError:
        start_date = first_day
    
    try:
        end_date = request.args.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = today
    except ValueError:
        end_date = today
    
    # Format dates for API
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Get billing data
    billing_data = usage_tracker.get_billing_data(user_id, start_str, end_str)
    
    return format_response(
        data=billing_data,
        message=f"Billing data from {start_str} to {end_str}",
        metadata={
            "period": {
                "start": start_str,
                "end": end_str
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/admin/billing/<user_id>', methods=['GET'])
@jwt_required
@admin_required
def admin_get_billing_data(user_id):
    """
    Get billing data for a specific user (admin only)
    
    Path parameters:
        user_id (str): User ID to get billing data for
    
    Query parameters:
        start_date (str): Start date in YYYY-MM-DD format (default: first day of current month)
        end_date (str): End date in YYYY-MM-DD format (default: today)
    
    Returns:
        JSON: Billing data for the specified user and period
    """
    # Get date parameters
    today = datetime.utcnow().date()
    first_day = today.replace(day=1)
    
    # Parse dates from query parameters
    try:
        start_date = request.args.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = first_day
    except ValueError:
        start_date = first_day
    
    try:
        end_date = request.args.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = today
    except ValueError:
        end_date = today
    
    # Format dates for API
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Get billing data
    billing_data = usage_tracker.get_billing_data(user_id, start_str, end_str)
    
    return format_response(
        data=billing_data,
        message=f"Billing data for user {user_id} from {start_str} to {end_str}",
        metadata={
            "period": {
                "start": start_str,
                "end": end_str
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/admin/summary', methods=['GET'])
@jwt_required
@admin_required
def admin_get_usage_summary():
    """
    Get overall usage summary for all users (admin only)
    
    Query parameters:
        days (int): Number of days to include in summary (default: 30)
    
    Returns:
        JSON: Overall usage summary
    """
    # Get days parameter
    try:
        days = int(request.args.get('days', 30))
        # Limit to reasonable range
        days = min(max(1, days), 90)
    except ValueError:
        days = 30
    
    # This would typically query a database for all users
    # For now, return a mock summary
    summary = {
        "period": f"Last {days} days",
        "total_requests": 12345,
        "unique_users": 123,
        "requests_by_category": {
            "ai": 8765,
            "multimodal": 3580
        },
        "requests_by_tier": {
            "free": 2345,
            "basic": 5678,
            "pro": 3456,
            "enterprise": 866
        },
        "compute_units": 5432,
        "tokens": 987654,
        "storage_bytes": 12345678,
        "daily_trend": []
    }
    
    # Generate daily trend data
    today = datetime.utcnow().date()
    for i in range(days):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        summary["daily_trend"].append({
            "date": date,
            "requests": int(12345 / days * (0.9 + 0.2 * (i % 7) / 6)),
            "compute_units": int(5432 / days * (0.9 + 0.2 * (i % 7) / 6)),
            "tokens": int(987654 / days * (0.9 + 0.2 * (i % 7) / 6))
        })
    
    return format_response(
        data=summary,
        message=f"Overall usage summary for the last {days} days",
        metadata={
            "period": f"Last {days} days",
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/admin/report/monthly', methods=['GET'])
@jwt_required
@admin_required
def admin_get_monthly_report():
    """
    Get monthly usage report (admin only)
    
    Query parameters:
        year (int): Year to get report for (default: current year)
        month (int): Month to get report for (default: current month)
    
    Returns:
        JSON: Monthly usage report
    """
    # Get date parameters
    today = datetime.utcnow().date()
    
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
        
        # Validate year and month
        if year < 2020 or year > today.year + 1:
            year = today.year
        if month < 1 or month > 12:
            month = today.month
    except ValueError:
        year = today.year
        month = today.month
    
    # This would typically query a database for monthly stats
    # For now, return a mock report
    month_name = datetime(year, month, 1).strftime('%B')
    
    report = {
        "period": f"{month_name} {year}",
        "summary": {
            "total_requests": 45678,
            "unique_users": 456,
            "compute_units": 23456,
            "tokens": 3456789,
            "storage_bytes": 45678901
        },
        "usage_by_tier": {
            "free": {
                "users": 234,
                "requests": 12345,
                "compute_units": 5678,
                "tokens": 876543,
                "revenue": 0
            },
            "basic": {
                "users": 123,
                "requests": 23456,
                "compute_units": 10987,
                "tokens": 1654321,
                "revenue": 1234.56
            },
            "pro": {
                "users": 78,
                "requests": 7654,
                "compute_units": 5432,
                "tokens": 765432,
                "revenue": 3456.78
            },
            "enterprise": {
                "users": 21,
                "requests": 2223,
                "compute_units": 1359,
                "tokens": 160493,
                "revenue": 4567.89
            }
        },
        "daily_stats": []
    }
    
    # Generate daily stats
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    
    for day in range(1, days_in_month + 1):
        # Skip future days
        if year == today.year and month == today.month and day > today.day:
            continue
            
        date_str = f"{year}-{month:02d}-{day:02d}"
        report["daily_stats"].append({
            "date": date_str,
            "requests": int(45678 / days_in_month * (0.8 + 0.4 * (day % 7) / 6)),
            "unique_users": int(456 * (0.7 + 0.3 * (day % 7) / 6)),
            "compute_units": int(23456 / days_in_month * (0.8 + 0.4 * (day % 7) / 6)),
            "tokens": int(3456789 / days_in_month * (0.8 + 0.4 * (day % 7) / 6))
        })
    
    # Calculate total revenue
    total_revenue = sum(
        tier_data["revenue"] 
        for tier, tier_data in report["usage_by_tier"].items()
    )
    report["summary"]["revenue"] = total_revenue
    
    return format_response(
        data=report,
        message=f"Monthly usage report for {month_name} {year}",
        metadata={
            "period": {
                "year": year,
                "month": month
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@usage_bp.route('/admin/limits', methods=['GET'])
@jwt_required
@admin_required
def get_rate_limits():
    """
    Get current rate limit configuration (admin only)
    
    Returns:
        JSON: Rate limit configuration
    """
    # Import rate_limiter to get tier limits
    from ..utils.rate_limiter import rate_limiter
    
    # Get tier limits for different window types
    limits = {
        'minute': {
            'free': rate_limiter.get_tier_limit('free', 'minute'),
            'basic': rate_limiter.get_tier_limit('basic', 'minute'),
            'pro': rate_limiter.get_tier_limit('pro', 'minute'),
            'enterprise': rate_limiter.get_tier_limit('enterprise', 'minute'),
        },
        'hour': {
            'free': rate_limiter.get_tier_limit('free', 'hour'),
            'basic': rate_limiter.get_tier_limit('basic', 'hour'),
            'pro': rate_limiter.get_tier_limit('pro', 'hour'),
            'enterprise': rate_limiter.get_tier_limit('enterprise', 'hour'),
        },
        'day': {
            'free': rate_limiter.get_tier_limit('free', 'day'),
            'basic': rate_limiter.get_tier_limit('basic', 'day'),
            'pro': rate_limiter.get_tier_limit('pro', 'day'),
            'enterprise': rate_limiter.get_tier_limit('enterprise', 'day'),
        }
    }
    
    return format_response(
        data=limits,
        message="Current rate limit configuration",
        metadata={
            "generated_at": datetime.utcnow().isoformat()
        }
    )
