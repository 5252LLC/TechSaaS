"""
Billing Service

Generates invoices based on usage data and handles billing-related operations.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
import redis
from flask import current_app
from .usage_tracker import usage_tracker

# Setup logger
logger = logging.getLogger(__name__)

class BillingService:
    """
    Service for generating invoices and calculating costs based on usage data.
    Integrates with the usage tracking system to retrieve usage metrics.
    """
    
    def __init__(self, redis_url=None):
        """
        Initialize the billing service.
        
        Args:
            redis_url (str, optional): Redis URL for caching billing data.
        """
        self.redis_url = redis_url
        self.redis = None
        if redis_url:
            try:
                self.redis = redis.from_url(redis_url)
                logger.info("BillingService connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
        
        # Pricing configuration - in a real system, this would come from a database
        self.pricing = {
            "free": {
                "base_fee": 0,
                "request_rate": 0,
                "compute_unit_rate": 0,
                "token_rate": 0,
                "storage_rate": 0
            },
            "basic": {
                "base_fee": 9.99,
                "request_rate": 0.001,  # $0.001 per request
                "compute_unit_rate": 0.01,  # $0.01 per compute unit
                "token_rate": 0.00001,  # $0.00001 per token
                "storage_rate": 0.00000001  # $0.00000001 per byte
            },
            "pro": {
                "base_fee": 49.99,
                "request_rate": 0.0005,  # $0.0005 per request
                "compute_unit_rate": 0.005,  # $0.005 per compute unit
                "token_rate": 0.000005,  # $0.000005 per token 
                "storage_rate": 0.000000005  # $0.000000005 per byte
            },
            "enterprise": {
                "base_fee": 199.99,
                "request_rate": 0.0002,  # $0.0002 per request
                "compute_unit_rate": 0.002,  # $0.002 per compute unit
                "token_rate": 0.000002,  # $0.000002 per token
                "storage_rate": 0.000000002  # $0.000000002 per byte
            }
        }
    
    def calculate_usage_cost(self, usage_data, tier="basic"):
        """
        Calculate cost based on usage data and subscription tier.
        
        Args:
            usage_data (dict): Usage data with metrics
            tier (str): Subscription tier (free, basic, pro, enterprise)
            
        Returns:
            dict: Cost breakdown
        """
        if tier not in self.pricing:
            tier = "basic"  # Default to basic if tier not found
        
        pricing = self.pricing[tier]
        
        # Extract usage metrics
        requests = usage_data.get("requests", {}).get("total", 0)
        compute_units = usage_data.get("metrics", {}).get("compute_units", 0)
        tokens = usage_data.get("metrics", {}).get("tokens", 0)
        storage_bytes = usage_data.get("metrics", {}).get("storage_bytes", 0)
        
        # Calculate costs
        request_cost = requests * pricing["request_rate"]
        compute_cost = compute_units * pricing["compute_unit_rate"]
        token_cost = tokens * pricing["token_rate"]
        storage_cost = storage_bytes * pricing["storage_rate"]
        
        # Total usage cost
        usage_cost = request_cost + compute_cost + token_cost + storage_cost
        
        # Total cost including base fee
        total_cost = pricing["base_fee"] + usage_cost
        
        return {
            "base_fee": round(pricing["base_fee"], 2),
            "usage_breakdown": {
                "request_cost": round(request_cost, 2),
                "compute_cost": round(compute_cost, 2),
                "token_cost": round(token_cost, 2),
                "storage_cost": round(storage_cost, 2)
            },
            "usage_cost": round(usage_cost, 2),
            "total_cost": round(total_cost, 2)
        }
    
    def generate_invoice(self, user_id, user_data, start_date, end_date, tier="basic"):
        """
        Generate an invoice for a user based on usage data.
        
        Args:
            user_id (str): User ID
            user_data (dict): User information (name, email, etc.)
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            tier (str): Subscription tier
            
        Returns:
            dict: Invoice data
        """
        # Get usage data for the billing period
        usage_data = usage_tracker.get_usage_summary(user_id, start_date=start_date, end_date=end_date)
        
        # Calculate costs
        cost_data = self.calculate_usage_cost(usage_data, tier)
        
        # Generate invoice
        invoice_id = str(uuid.uuid4())
        invoice_date = datetime.utcnow().strftime("%Y-%m-%d")
        due_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        invoice = {
            "invoice_id": invoice_id,
            "user_id": user_id,
            "invoice_date": invoice_date,
            "due_date": due_date,
            "billing_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "user_info": user_data,
            "subscription_tier": tier,
            "usage_summary": {
                "requests": usage_data.get("requests", {}).get("total", 0),
                "compute_units": usage_data.get("metrics", {}).get("compute_units", 0),
                "tokens": usage_data.get("metrics", {}).get("tokens", 0),
                "storage_bytes": usage_data.get("metrics", {}).get("storage_bytes", 0)
            },
            "line_items": [
                {
                    "description": f"{tier.capitalize()} Subscription",
                    "amount": cost_data["base_fee"],
                    "type": "subscription"
                },
                {
                    "description": f"API Requests ({usage_data.get('requests', {}).get('total', 0)})",
                    "amount": cost_data["usage_breakdown"]["request_cost"],
                    "type": "usage"
                },
                {
                    "description": f"Compute Units ({usage_data.get('metrics', {}).get('compute_units', 0)})",
                    "amount": cost_data["usage_breakdown"]["compute_cost"],
                    "type": "usage"
                },
                {
                    "description": f"Tokens ({usage_data.get('metrics', {}).get('tokens', 0)})",
                    "amount": cost_data["usage_breakdown"]["token_cost"],
                    "type": "usage"
                },
                {
                    "description": f"Storage ({self._format_storage(usage_data.get('metrics', {}).get('storage_bytes', 0))})",
                    "amount": cost_data["usage_breakdown"]["storage_cost"],
                    "type": "usage"
                }
            ],
            "subtotal": cost_data["base_fee"] + cost_data["usage_cost"],
            "total": cost_data["total_cost"],
            "currency": "USD",
            "status": "draft"
        }
        
        # Cache invoice in Redis if available
        if self.redis:
            try:
                invoice_key = f"invoice:{user_id}:{invoice_id}"
                self.redis.setex(invoice_key, 86400 * 30, json.dumps(invoice))  # 30 days expiry
                logger.info(f"Invoice {invoice_id} cached in Redis")
            except Exception as e:
                logger.error(f"Failed to cache invoice in Redis: {e}")
        
        return invoice
    
    def get_invoice(self, invoice_id):
        """
        Retrieve an invoice by ID.
        
        Args:
            invoice_id (str): Invoice ID
            
        Returns:
            dict: Invoice data or None if not found
        """
        # In a real system, this would query a database
        # For now, we'll try to get it from Redis if available
        if self.redis:
            try:
                # Search for the invoice using pattern matching
                pattern = f"invoice:*:{invoice_id}"
                keys = self.redis.keys(pattern)
                
                if keys and len(keys) > 0:
                    invoice_data = self.redis.get(keys[0])
                    if invoice_data:
                        return json.loads(invoice_data)
            except Exception as e:
                logger.error(f"Failed to retrieve invoice from Redis: {e}")
        
        return None
    
    def get_user_invoices(self, user_id, limit=10):
        """
        Get recent invoices for a user.
        
        Args:
            user_id (str): User ID
            limit (int): Maximum number of invoices to return
            
        Returns:
            list: List of invoice data
        """
        # In a real system, this would query a database
        # For now, we'll try to get it from Redis if available
        invoices = []
        
        if self.redis:
            try:
                # Search for invoices using pattern matching
                pattern = f"invoice:{user_id}:*"
                keys = self.redis.keys(pattern)
                
                # Sort by creation time (newest first)
                keys.sort(reverse=True)
                
                # Limit the number of results
                keys = keys[:limit]
                
                for key in keys:
                    invoice_data = self.redis.get(key)
                    if invoice_data:
                        invoices.append(json.loads(invoice_data))
            except Exception as e:
                logger.error(f"Failed to retrieve user invoices from Redis: {e}")
        
        return invoices
    
    def finalize_invoice(self, invoice_id, payment_info=None):
        """
        Finalize an invoice by changing its status from draft to final.
        
        Args:
            invoice_id (str): Invoice ID
            payment_info (dict, optional): Payment information
            
        Returns:
            dict: Updated invoice or None if not found
        """
        invoice = self.get_invoice(invoice_id)
        
        if not invoice:
            return None
        
        # Update invoice status
        invoice["status"] = "final"
        
        # Add payment info if provided
        if payment_info:
            invoice["payment_info"] = payment_info
        
        # Update the invoice in Redis
        if self.redis:
            try:
                invoice_key = f"invoice:{invoice['user_id']}:{invoice_id}"
                self.redis.setex(invoice_key, 86400 * 30, json.dumps(invoice))  # 30 days expiry
                logger.info(f"Invoice {invoice_id} status updated to final")
            except Exception as e:
                logger.error(f"Failed to update invoice in Redis: {e}")
        
        return invoice
    
    def _format_storage(self, bytes_value):
        """
        Format storage bytes to human-readable format.
        
        Args:
            bytes_value (int): Size in bytes
            
        Returns:
            str: Formatted size string
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(bytes_value)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"


# Create a singleton instance
billing_service = BillingService()

def init_app(app):
    """
    Initialize the billing service with the Flask app context.
    
    Args:
        app: Flask application instance
    """
    global billing_service
    
    redis_url = app.config.get("REDIS_URL")
    if redis_url:
        billing_service = BillingService(redis_url=redis_url)
    
    # Make billing service available in app context
    app.billing_service = billing_service
