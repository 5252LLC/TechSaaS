# Billing System: Implementation Guide

This guide provides detailed implementation patterns and code examples for working with the TechSaaS billing system. It's intended for experienced developers who need to integrate with our billing infrastructure.

## Overview

The billing system provides a complete pipeline for:
- Usage tracking across multiple metrics
- Consumption-based pricing calculation
- Invoice generation and management
- Subscription tier enforcement

## Quick Reference

```python
# Python SDK Example
from techsaas import Client

# Initialize client
client = Client(api_key="your_api_key")

# Get current billing information
invoice = client.billing.get_current_invoice()
print(f"Current month charges: ${invoice.total}")

# Get billing history
invoices = client.billing.get_invoice_history(limit=5)
for inv in invoices:
    print(f"Invoice {inv.invoice_id}: ${inv.total} ({inv.status})")

# Get pricing information
pricing = client.billing.get_pricing()
for tier, details in pricing.tiers.items():
    print(f"{tier.capitalize()}: ${details.base_fee_monthly}/month")
```

```javascript
// JavaScript SDK Example
import { TechSaasClient } from '@techsaas/sdk';

// Initialize client
const client = new TechSaasClient({
  apiKey: 'your_api_key'
});

// Get current billing information
client.billing.getCurrentInvoice()
  .then(invoice => {
    console.log(`Current month charges: $${invoice.total}`);
  });

// Get billing history
client.billing.getInvoiceHistory({ limit: 5 })
  .then(invoices => {
    invoices.forEach(inv => {
      console.log(`Invoice ${inv.invoiceId}: $${inv.total} (${inv.status})`);
    });
  });

// Get pricing information
client.billing.getPricing()
  .then(pricing => {
    Object.entries(pricing.tiers).forEach(([tier, details]) => {
      console.log(`${tier.charAt(0).toUpperCase() + tier.slice(1)}: $${details.baseFeeMonthly}/month`);
    });
  });
```

## Billing Architecture

The billing system consists of several integrated components:

1. **Usage Tracking** - Captures and stores API consumption metrics
2. **Rate Limiting** - Enforces tier-based request limits
3. **Cost Calculation** - Converts usage metrics to billable amounts
4. **Invoice Generation** - Creates and manages invoice records
5. **Reporting** - Provides analytics and usage insights

![Billing System Architecture](../assets/images/billing-architecture.png)

## Usage Metric Tracking

The system tracks several types of metrics for billing purposes:

| Metric | Description | Pricing Unit |
|--------|-------------|--------------|
| Requests | API calls | Per request |
| Compute Units | Processing resources | Per unit |
| Tokens | AI operation tokens | Per token |
| Storage | Data storage | Per byte |

### Tracking Custom Metrics

You can track custom metrics for your API endpoints:

```python
@app.route('/api/v1/custom-endpoint', methods=['POST'])
@jwt_required
@track_usage('custom', 'operation_name')
def custom_endpoint():
    # Calculate metrics
    compute_units = calculate_compute_units(request.json)
    tokens = calculate_tokens(request.json)
    
    # Track custom metrics
    g.track_metrics = {
        'compute_units': compute_units,
        'tokens': tokens,
        'custom_metric': 42
    }
    
    # Process request
    result = process_request(request.json)
    
    return jsonify(result)
```

## Cost Calculation Implementation

The billing system calculates costs using a multi-component pricing model:

```python
def calculate_usage_cost(usage_data, tier="basic"):
    """
    Cost calculation algorithm implementation
    """
    pricing = TIER_PRICING[tier]
    
    # Extract usage metrics
    requests = usage_data.get("requests", {}).get("total", 0)
    compute_units = usage_data.get("metrics", {}).get("compute_units", 0)
    tokens = usage_data.get("metrics", {}).get("tokens", 0)
    storage_bytes = usage_data.get("metrics", {}).get("storage_bytes", 0)
    
    # Apply volume discounts based on usage brackets
    request_cost = calculate_with_volume_discount(
        requests, 
        pricing["request_rate"],
        volume_discount_brackets["requests"]
    )
    
    compute_cost = calculate_with_volume_discount(
        compute_units, 
        pricing["compute_unit_rate"],
        volume_discount_brackets["compute"]
    )
    
    token_cost = tokens * pricing["token_rate"]
    storage_cost = storage_bytes * pricing["storage_rate"]
    
    # Total usage cost
    usage_cost = request_cost + compute_cost + token_cost + storage_cost
    
    # Apply tier discount if applicable
    if "tier_discount" in pricing:
        usage_cost = usage_cost * (1 - pricing["tier_discount"])
    
    # Total cost including base fee
    total_cost = pricing["base_fee"] + usage_cost
    
    return {
        "base_fee": pricing["base_fee"],
        "usage_breakdown": {
            "request_cost": request_cost,
            "compute_cost": compute_cost,
            "token_cost": token_cost,
            "storage_cost": storage_cost
        },
        "usage_cost": usage_cost,
        "total_cost": total_cost
    }

def calculate_with_volume_discount(quantity, base_rate, brackets):
    """
    Apply volume-based discount tiers
    """
    cost = 0
    remaining = quantity
    
    for bracket in sorted(brackets.keys()):
        if remaining <= 0:
            break
            
        discount = brackets[bracket]
        
        if bracket == "max":
            # Apply rate to all remaining quantity
            cost += remaining * base_rate * (1 - discount)
            remaining = 0
        else:
            bracket_limit = int(bracket)
            
            if remaining > bracket_limit:
                # Apply rate to this bracket's quantity
                bracket_quantity = bracket_limit
                cost += bracket_quantity * base_rate * (1 - discount)
                remaining -= bracket_quantity
            else:
                # Apply rate to remaining quantity
                cost += remaining * base_rate * (1 - discount)
                remaining = 0
    
    return cost
```

## Invoice Generation

The system generates invoices based on usage data:

```python
def generate_invoice(user_id, billing_period):
    """
    Generate an invoice for a user's billing period
    """
    start_date, end_date = billing_period
    
    # Get user info
    user = get_user(user_id)
    tier = user.subscription_tier
    
    # Get usage data for period
    usage_data = get_usage_data(user_id, start_date, end_date)
    
    # Calculate costs
    costs = calculate_usage_cost(usage_data, tier)
    
    # Create line items
    line_items = [
        {
            "description": f"{tier.capitalize()} Subscription",
            "amount": costs["base_fee"],
            "type": "subscription"
        }
    ]
    
    # Add usage line items
    for metric, cost in costs["usage_breakdown"].items():
        if cost > 0:
            line_items.append({
                "description": f"{metric.replace('_', ' ').title()} ({usage_data['metrics'].get(metric.replace('_cost', ''), 0)})",
                "amount": cost,
                "type": "usage"
            })
    
    # Create invoice
    invoice = {
        "invoice_id": generate_uuid(),
        "user_id": user_id,
        "invoice_date": current_date(),
        "due_date": current_date() + 30_days,
        "billing_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "user_info": {
            "name": user.name,
            "email": user.email,
            "address": user.address
        },
        "subscription_tier": tier,
        "line_items": line_items,
        "subtotal": costs["base_fee"] + costs["usage_cost"],
        "total": costs["total_cost"],
        "currency": "USD",
        "status": "draft"
    }
    
    # Store invoice
    store_invoice(invoice)
    
    return invoice
```

## Webhooks Integration

### Receiving Billing Webhooks

You can receive notifications about billing events by configuring webhooks:

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

WEBHOOK_SECRET = "your_webhook_secret"

@app.route('/webhooks/techsaas-billing', methods=['POST'])
def billing_webhook():
    # Verify webhook signature
    signature = request.headers.get('X-TechSaaS-Signature')
    payload = request.data
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process webhook event
    event = request.json
    event_type = event.get('type')
    
    if event_type == 'invoice.created':
        # Handle new invoice
        invoice = event.get('data')
        # Store invoice in your system
        # Notify users
        
    elif event_type == 'invoice.finalized':
        # Handle finalized invoice
        invoice = event.get('data')
        # Update invoice status
        # Process payment
        
    elif event_type == 'payment.succeeded':
        # Handle successful payment
        payment = event.get('data')
        # Update payment status
        # Send receipt
        
    elif event_type == 'payment.failed':
        # Handle failed payment
        payment = event.get('data')
        # Flag account for payment issue
        # Notify user
    
    return jsonify({"status": "success"}), 200
```

### Webhook Event Types

| Event Type | Description |
|------------|-------------|
| invoice.created | A new invoice has been generated |
| invoice.finalized | An invoice has been finalized |
| payment.succeeded | A payment has been successfully processed |
| payment.failed | A payment attempt has failed |

## Tier-Based Rate Limiting

Use our rate limits implementation to enforce tier-based request limits:

```python
from flask import Flask, request, g, jsonify
import redis
import time

app = Flask(__name__)
redis_client = redis.from_url("redis://localhost:6379/0")

# Tier-based rate limits (requests per minute)
RATE_LIMITS = {
    "free": 20,
    "basic": 100,
    "pro": 500,
    "enterprise": 2000
}

def check_rate_limit(user_id, tier):
    """Check if user has exceeded their rate limit"""
    # Calculate current time window (1-minute window)
    window = int(time.time() / 60)
    
    # Create a rate limit key for this user and time window
    rate_key = f"rate:{user_id}:{window}"
    
    # Get the user's limit based on their tier
    limit = RATE_LIMITS.get(tier, RATE_LIMITS["basic"])
    
    # Increment the counter and get the current value
    current = redis_client.incr(rate_key)
    
    # Set expiry to ensure cleanup (2 minutes)
    if current == 1:
        redis_client.expire(rate_key, 120)
    
    # Check if user has exceeded their limit
    return current <= limit, current, limit, 60 - (int(time.time()) % 60)

@app.route('/api/v1/protected-endpoint', methods=['POST'])
def protected_endpoint():
    # Authenticate user (simplified)
    user_id = request.headers.get('X-User-ID')
    tier = request.headers.get('X-User-Tier', 'basic')
    
    # Check rate limit
    allowed, current, limit, reset = check_rate_limit(user_id, tier)
    
    # Set rate limit headers
    response_headers = {
        'X-RateLimit-Limit': str(limit),
        'X-RateLimit-Remaining': str(max(0, limit - current)),
        'X-RateLimit-Reset': str(reset)
    }
    
    if not allowed:
        # User has exceeded their rate limit
        return jsonify({
            "status": "error",
            "message": "Rate limit exceeded",
            "error": {
                "detail": f"Minute limit of {limit} requests exceeded",
                "status": "too_many_requests",
                "limit": limit,
                "current": current,
                "retry_after": reset
            }
        }), 429, response_headers
    
    # Process the request
    # ...
    
    # Return response with rate limit headers
    return jsonify({
        "status": "success",
        "message": "Operation successful",
        "data": {"result": "example"}
    }), 200, response_headers
```

## Database Schema for Billing

Here's a PostgreSQL schema for billing-related tables:

```sql
-- Users table (assumed to exist)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'basic'
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    base_fee DECIMAL(10, 2) NOT NULL,
    usage_amount DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Invoice line items
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id UUID PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    description TEXT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    type VARCHAR(20) NOT NULL,
    metadata JSONB
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    payment_reference VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    payment_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoice_line_items_invoice_id ON invoice_line_items(invoice_id);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
```

## Integration with Payment Providers

### Stripe Integration Example

```python
import stripe
from flask import Flask, request, jsonify

app = Flask(__name__)
stripe.api_key = "your_stripe_api_key"

@app.route('/api/v1/billing/pay-invoice/<invoice_id>', methods=['POST'])
def pay_invoice(invoice_id):
    # Get invoice from database
    invoice = get_invoice(invoice_id)
    user = get_user(invoice['user_id'])
    
    # Create payment intent
    payment_intent = stripe.PaymentIntent.create(
        amount=int(invoice['total'] * 100),  # Convert to cents
        currency=invoice['currency'].lower(),
        customer=user['stripe_customer_id'],
        metadata={
            'invoice_id': invoice_id,
            'user_id': invoice['user_id']
        }
    )
    
    # Return client secret for frontend to complete payment
    return jsonify({
        'client_secret': payment_intent.client_secret
    })

@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    # Verify webhook signature
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, "your_webhook_signing_secret"
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        invoice_id = payment_intent['metadata']['invoice_id']
        
        # Update invoice payment status
        mark_invoice_paid(
            invoice_id, 
            payment_intent['id'],
            payment_intent['amount'] / 100
        )
        
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        invoice_id = payment_intent['metadata']['invoice_id']
        
        # Mark invoice payment as failed
        mark_invoice_payment_failed(
            invoice_id,
            payment_intent['id'],
            payment_intent['last_payment_error']['message']
        )
    
    return jsonify({'status': 'success'})
```

## Scheduled Billing Tasks

### Monthly Invoice Generation

```python
import schedule
import time
from datetime import datetime, timedelta

def generate_monthly_invoices():
    """Generate invoices for all users for the previous month"""
    # Calculate billing period
    today = datetime.utcnow().date()
    first_day_current = today.replace(day=1)
    last_day_previous = first_day_current - timedelta(days=1)
    first_day_previous = last_day_previous.replace(day=1)
    
    # Format dates
    start_date = first_day_previous.strftime('%Y-%m-%d')
    end_date = last_day_previous.strftime('%Y-%m-%d')
    
    # Get all active users
    users = get_all_active_users()
    
    # Track results
    results = {
        "success": 0,
        "failed": 0,
        "invoices": []
    }
    
    # Generate invoices for each user
    for user in users:
        try:
            # Generate invoice
            invoice = generate_invoice(
                user_id=user['id'],
                user_data=user,
                start_date=start_date,
                end_date=end_date,
                tier=user['tier']
            )
            
            # Finalize the invoice
            invoice = finalize_invoice(invoice["invoice_id"])
            
            # Add to results
            results["invoices"].append({
                "user_id": user['id'],
                "invoice_id": invoice["invoice_id"],
                "amount": invoice["total"]
            })
            
            results["success"] += 1
        except Exception as e:
            print(f"Failed to generate invoice for user {user['id']}: {e}")
            results["failed"] += 1
    
    print(f"Generated {results['success']} invoices for {start_date} to {end_date}")
    return results

# Schedule monthly invoice generation
schedule.every().month.at("00:00").do(generate_monthly_invoices)

# Run the scheduling
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Error Handling and Edge Cases

### Handling Missing Usage Data

```python
def get_usage_with_fallback(user_id, start_date, end_date):
    """
    Get usage data with fallback to zero values if missing
    """
    try:
        usage_data = get_usage_data(user_id, start_date, end_date)
        
        if not usage_data:
            # No usage data found, create default structure
            usage_data = {
                "requests": {
                    "total": 0,
                    "by_category": {}
                },
                "metrics": {
                    "compute_units": 0,
                    "tokens": 0,
                    "storage_bytes": 0
                }
            }
    except Exception as e:
        print(f"Error retrieving usage data: {e}")
        # Create default structure on error
        usage_data = {
            "requests": {
                "total": 0,
                "by_category": {}
            },
            "metrics": {
                "compute_units": 0,
                "tokens": 0,
                "storage_bytes": 0
            }
        }
    
    return usage_data
```

### Handling Tier Changes

```python
def handle_tier_change(user_id, old_tier, new_tier, change_date):
    """
    Handle a user's tier change during a billing period
    """
    # Calculate pro-rated amounts for each tier
    
    # Get the current month's start
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    
    # If change happens in a different month, nothing to pro-rate
    if change_date.month != today.month or change_date.year != today.year:
        return
    
    # Calculate days in month
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    
    days_in_month = (next_month - month_start).days
    
    # Calculate days at each tier
    days_at_old_tier = (change_date - month_start).days
    days_at_new_tier = days_in_month - days_at_old_tier
    
    # Get tier pricing
    old_pricing = TIER_PRICING[old_tier]
    new_pricing = TIER_PRICING[new_tier]
    
    # Calculate pro-rated base fees
    old_tier_fee = (old_pricing["base_fee"] / days_in_month) * days_at_old_tier
    new_tier_fee = (new_pricing["base_fee"] / days_in_month) * days_at_new_tier
    
    # Store pro-rated fee information for invoice generation
    store_prorated_fees(
        user_id, 
        {
            "old_tier": old_tier,
            "new_tier": new_tier,
            "change_date": change_date.strftime('%Y-%m-%d'),
            "days_in_month": days_in_month,
            "days_at_old_tier": days_at_old_tier,
            "days_at_new_tier": days_at_new_tier,
            "old_tier_fee": old_tier_fee,
            "new_tier_fee": new_tier_fee,
            "total_base_fee": old_tier_fee + new_tier_fee
        }
    )
```

## Performance Optimization

### Caching Strategies

```python
import redis
import json
from functools import wraps

# Connect to Redis
redis_client = redis.from_url("redis://localhost:6379/0")

def cache_result(key_prefix, ttl=3600):
    """
    Decorator to cache function results in Redis
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function arguments
            key_parts = [key_prefix]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # Try to get cached result
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Example usage with invoice generation
@cache_result("invoice", ttl=300)  # 5 minute cache
def get_invoice(invoice_id):
    # Expensive database query
    return database.query(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")

# Example usage with pricing
@cache_result("pricing", ttl=86400)  # 24 hour cache
def get_pricing():
    # Fetch pricing from configuration database
    return pricing_service.get_current_pricing()
```

## Advanced Usage Metrics

### Custom Metrics Definition

```python
class CustomMetricsTracker:
    """
    Track custom metrics for advanced billing scenarios
    """
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def track_metric(self, user_id, metric_name, value, metadata=None):
        """
        Track a custom metric value
        """
        # Get current day
        day = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Create metric keys
        daily_key = f"metric:{user_id}:{day}:{metric_name}"
        monthly_key = f"metric:{user_id}:{day[:7]}:{metric_name}"
        
        # Store the metric value
        self.redis.incrbyfloat(daily_key, float(value))
        self.redis.incrbyfloat(monthly_key, float(value))
        
        # Set expiry for keys
        self.redis.expire(daily_key, 86400 * 7)  # 7 days
        self.redis.expire(monthly_key, 86400 * 32)  # ~1 month
        
        # If metadata provided, store in a separate hash
        if metadata:
            metadata_key = f"metric_meta:{user_id}:{day}:{metric_name}"
            self.redis.hset(metadata_key, mapping=metadata)
            self.redis.expire(metadata_key, 86400 * 7)  # 7 days
    
    def get_daily_metric(self, user_id, metric_name, day=None):
        """
        Get a daily metric value
        """
        if day is None:
            day = datetime.utcnow().strftime('%Y-%m-%d')
            
        daily_key = f"metric:{user_id}:{day}:{metric_name}"
        value = self.redis.get(daily_key)
        
        return float(value) if value else 0.0
    
    def get_monthly_metric(self, user_id, metric_name, month=None):
        """
        Get a monthly metric value
        """
        if month is None:
            month = datetime.utcnow().strftime('%Y-%m')
            
        monthly_key = f"metric:{user_id}:{month}:{metric_name}"
        value = self.redis.get(monthly_key)
        
        return float(value) if value else 0.0

# Example usage
metrics = CustomMetricsTracker(redis_client)

# Track a custom model training metric
metrics.track_metric(
    user_id="user123",
    metric_name="model_training_time",
    value=345.6,  # seconds
    metadata={
        "model_type": "classification",
        "parameters": 1250000,
        "accuracy": 0.92
    }
)
```

## Audit Trail

### Billing Event Logging

```python
def log_billing_event(user_id, event_type, details, actor_id=None):
    """
    Log a billing event for audit purposes
    """
    event = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": event_type,
        "details": details,
        "actor_id": actor_id,
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": request.remote_addr if request else None,
        "user_agent": request.user_agent.string if request and request.user_agent else None
    }
    
    # Store in database
    db.billing_events.insert_one(event)
    
    # For high-value events, also log to a separate security audit
    if event_type in ['invoice.adjustment', 'payment.refund', 'tier.change']:
        db.security_audit.insert_one(event)
    
    return event

# Example usage
log_billing_event(
    user_id="user123",
    event_type="invoice.adjustment",
    details={
        "invoice_id": "inv_123456",
        "original_amount": 123.45,
        "adjusted_amount": 100.00,
        "reason": "Service outage compensation",
        "note": "Approved by management"
    },
    actor_id="admin_user456"
)
```

This documentation provides you with the essential patterns and code examples to integrate with the TechSaaS billing system.
