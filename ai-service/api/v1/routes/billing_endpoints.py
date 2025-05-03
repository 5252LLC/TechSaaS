"""
Billing Endpoints

API routes for generating invoices, retrieving invoice history, and managing billing operations.
These endpoints integrate with the billing service to provide financial operations based on usage data.
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime, timedelta
import logging
import json

from ..middleware.security import jwt_required
from ..middleware.authorization import admin_required, has_permission
from ..utils.response_formatter import format_response
from ..utils.billing_service import billing_service

# Setup logger
logger = logging.getLogger(__name__)

# Blueprint definition
billing_bp = Blueprint('billing', __name__, url_prefix='/billing')


@billing_bp.route('/invoice', methods=['GET'])
@jwt_required
def get_current_invoice():
    """
    Get the current billing period invoice for the authenticated user
    
    Returns:
        JSON: Current invoice data
    """
    # Get user ID from JWT token
    user_id = g.current_user.get('sub')
    tier = g.current_user.get('tier', 'basic')
    
    # Get user info - in a real system this would come from a user service
    user_data = {
        "id": user_id,
        "name": g.current_user.get('name', 'User'),
        "email": g.current_user.get('email', f'{user_id}@example.com'),
        "address": g.current_user.get('address', {})
    }
    
    # Calculate billing period (current month)
    today = datetime.utcnow().date()
    start_date = today.replace(day=1).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    # Generate invoice for current period
    invoice = billing_service.generate_invoice(
        user_id=user_id,
        user_data=user_data,
        start_date=start_date,
        end_date=end_date,
        tier=tier
    )
    
    return format_response(
        data=invoice,
        message="Current billing period invoice",
        metadata={
            "period": {
                "start": start_date,
                "end": end_date
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/invoices/history', methods=['GET'])
@jwt_required
def get_invoice_history():
    """
    Get invoice history for the authenticated user
    
    Query parameters:
        limit (int): Maximum number of invoices to return (default: 10)
    
    Returns:
        JSON: List of invoices
    """
    # Get user ID from JWT token
    user_id = g.current_user.get('sub')
    
    # Get limit parameter
    try:
        limit = int(request.args.get('limit', 10))
        # Limit to reasonable range
        limit = min(max(1, limit), 100)
    except ValueError:
        limit = 10
    
    # Get invoice history
    invoices = billing_service.get_user_invoices(user_id, limit=limit)
    
    return format_response(
        data=invoices,
        message=f"Invoice history (last {len(invoices)} invoices)",
        metadata={
            "count": len(invoices),
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/invoice/<invoice_id>', methods=['GET'])
@jwt_required
def get_invoice_by_id(invoice_id):
    """
    Get a specific invoice by ID
    
    Path parameters:
        invoice_id (str): Invoice ID
    
    Returns:
        JSON: Invoice data
    """
    # Get user ID from JWT token
    user_id = g.current_user.get('sub')
    
    # Get invoice
    invoice = billing_service.get_invoice(invoice_id)
    
    if not invoice:
        return format_response(
            message="Invoice not found",
            status="error",
            status_code=404
        )
    
    # Check if invoice belongs to the user or user is admin
    if invoice.get('user_id') != user_id and not g.current_user.get('is_admin', False):
        return format_response(
            message="You don't have permission to access this invoice",
            status="error",
            status_code=403
        )
    
    return format_response(
        data=invoice,
        message="Invoice details",
        metadata={
            "invoice_id": invoice_id,
            "retrieved_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/invoice/<invoice_id>/finalize', methods=['POST'])
@jwt_required
@admin_required
def finalize_invoice(invoice_id):
    """
    Finalize an invoice (admin only)
    
    Path parameters:
        invoice_id (str): Invoice ID
    
    Request body:
        payment_info (dict, optional): Payment information
    
    Returns:
        JSON: Updated invoice data
    """
    # Get payment info from request body
    payment_info = request.json.get('payment_info')
    
    # Finalize invoice
    invoice = billing_service.finalize_invoice(invoice_id, payment_info)
    
    if not invoice:
        return format_response(
            message="Invoice not found",
            status="error",
            status_code=404
        )
    
    return format_response(
        data=invoice,
        message="Invoice finalized",
        metadata={
            "invoice_id": invoice_id,
            "finalized_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/admin/generate-invoice', methods=['POST'])
@jwt_required
@admin_required
def admin_generate_invoice():
    """
    Generate an invoice for a specific user (admin only)
    
    Request body:
        user_id (str): User ID
        user_data (dict): User information
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        tier (str, optional): Subscription tier (default: basic)
    
    Returns:
        JSON: Generated invoice
    """
    # Get request parameters
    data = request.json
    
    if not data:
        return format_response(
            message="Missing request body",
            status="error",
            status_code=400
        )
    
    user_id = data.get('user_id')
    user_data = data.get('user_data')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    tier = data.get('tier', 'basic')
    
    # Validate required parameters
    if not all([user_id, user_data, start_date, end_date]):
        return format_response(
            message="Missing required parameters: user_id, user_data, start_date, end_date",
            status="error",
            status_code=400
        )
    
    # Generate invoice
    invoice = billing_service.generate_invoice(
        user_id=user_id,
        user_data=user_data,
        start_date=start_date,
        end_date=end_date,
        tier=tier
    )
    
    return format_response(
        data=invoice,
        message="Invoice generated",
        metadata={
            "period": {
                "start": start_date,
                "end": end_date
            },
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/admin/monthly-batch', methods=['POST'])
@jwt_required
@admin_required
def admin_generate_monthly_batch():
    """
    Generate monthly invoices for all users (admin only)
    
    Request body:
        year (int, optional): Year to generate invoices for (default: current year)
        month (int, optional): Month to generate invoices for (default: previous month)
        users (list, optional): List of user IDs to generate invoices for (default: all users)
    
    Returns:
        JSON: Summary of generated invoices
    """
    # Get request parameters
    data = request.json or {}
    
    # Calculate default year and month (previous month)
    today = datetime.utcnow().date()
    first_day_current = today.replace(day=1)
    last_day_previous = first_day_current - timedelta(days=1)
    default_year = last_day_previous.year
    default_month = last_day_previous.month
    
    year = data.get('year', default_year)
    month = data.get('month', default_month)
    users = data.get('users', [])
    
    # Validate year and month
    try:
        year = int(year)
        month = int(month)
        if month < 1 or month > 12:
            month = default_month
    except (ValueError, TypeError):
        year = default_year
        month = default_month
    
    # This would typically query a user database to get all user IDs
    # For mock purposes, we'll use a predefined list if none provided
    if not users:
        # Mock user list
        users = [
            {
                "id": "user123",
                "data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "address": {
                        "street": "123 Main St",
                        "city": "Anytown",
                        "state": "CA",
                        "zip": "12345"
                    }
                },
                "tier": "basic"
            },
            {
                "id": "user456",
                "data": {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "address": {
                        "street": "456 Oak Ave",
                        "city": "Somewhere",
                        "state": "NY",
                        "zip": "67890"
                    }
                },
                "tier": "pro"
            }
        ]
    
    # Calculate billing period
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{days_in_month:02d}"
    
    # Track results
    results = {
        "success": 0,
        "failed": 0,
        "invoices": []
    }
    
    # Generate invoices for each user
    for user in users:
        try:
            # Extract user data
            if isinstance(user, dict):
                user_id = user.get("id")
                user_data = user.get("data", {})
                tier = user.get("tier", "basic")
            else:
                user_id = user
                # In a real system, we would query a user service to get user data
                user_data = {
                    "name": f"User {user_id}",
                    "email": f"{user_id}@example.com"
                }
                tier = "basic"
            
            # Generate invoice
            invoice = billing_service.generate_invoice(
                user_id=user_id,
                user_data=user_data,
                start_date=start_date,
                end_date=end_date,
                tier=tier
            )
            
            # Finalize the invoice
            invoice = billing_service.finalize_invoice(invoice["invoice_id"])
            
            # Add to results
            results["invoices"].append({
                "user_id": user_id,
                "invoice_id": invoice["invoice_id"],
                "amount": invoice["total"]
            })
            
            results["success"] += 1
        except Exception as e:
            logger.error(f"Failed to generate invoice for user {user_id}: {e}")
            results["failed"] += 1
    
    return format_response(
        data=results,
        message=f"Generated {results['success']} invoices for {year}-{month:02d}",
        metadata={
            "period": {
                "year": year,
                "month": month,
                "start_date": start_date,
                "end_date": end_date
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    )


@billing_bp.route('/pricing', methods=['GET'])
def get_pricing_info():
    """
    Get pricing information for all subscription tiers
    
    Returns:
        JSON: Pricing information
    """
    # Get pricing information from billing service
    pricing = billing_service.pricing
    
    # Format for API response
    pricing_info = {
        "tiers": {
            "free": {
                "name": "Free",
                "base_fee_monthly": pricing["free"]["base_fee"],
                "api_request_rate": pricing["free"]["request_rate"],
                "compute_unit_rate": pricing["free"]["compute_unit_rate"],
                "token_rate": pricing["free"]["token_rate"],
                "storage_rate": pricing["free"]["storage_rate"],
                "features": [
                    "20 requests per minute",
                    "1,000 requests per day",
                    "Basic AI functionality",
                    "Community support"
                ]
            },
            "basic": {
                "name": "Basic",
                "base_fee_monthly": pricing["basic"]["base_fee"],
                "api_request_rate": pricing["basic"]["request_rate"],
                "compute_unit_rate": pricing["basic"]["compute_unit_rate"],
                "token_rate": pricing["basic"]["token_rate"],
                "storage_rate": pricing["basic"]["storage_rate"],
                "features": [
                    "100 requests per minute",
                    "10,000 requests per day",
                    "All AI functionality",
                    "Email support",
                    "API key management"
                ]
            },
            "pro": {
                "name": "Professional",
                "base_fee_monthly": pricing["pro"]["base_fee"],
                "api_request_rate": pricing["pro"]["request_rate"],
                "compute_unit_rate": pricing["pro"]["compute_unit_rate"],
                "token_rate": pricing["pro"]["token_rate"],
                "storage_rate": pricing["pro"]["storage_rate"],
                "features": [
                    "500 requests per minute",
                    "100,000 requests per day",
                    "Advanced models",
                    "Priority support",
                    "Team management",
                    "Usage analytics"
                ]
            },
            "enterprise": {
                "name": "Enterprise",
                "base_fee_monthly": pricing["enterprise"]["base_fee"],
                "api_request_rate": pricing["enterprise"]["request_rate"],
                "compute_unit_rate": pricing["enterprise"]["compute_unit_rate"],
                "token_rate": pricing["enterprise"]["token_rate"],
                "storage_rate": pricing["enterprise"]["storage_rate"],
                "features": [
                    "2,000 requests per minute",
                    "Unlimited daily requests",
                    "Custom models",
                    "Dedicated support",
                    "SLA guarantees",
                    "On-premises deployment options",
                    "Custom integrations"
                ]
            }
        },
        "currency": "USD",
        "billing_cycles": ["monthly", "annual"],
        "payment_methods": ["credit_card", "invoice", "wire_transfer"],
        "volume_discounts": {
            "requests": {
                "100k+": "10% discount",
                "1M+": "15% discount",
                "10M+": "25% discount"
            },
            "compute_units": {
                "1k+": "10% discount",
                "10k+": "15% discount",
                "100k+": "25% discount"
            }
        }
    }
    
    return format_response(
        data=pricing_info,
        message="Current pricing information"
    )
