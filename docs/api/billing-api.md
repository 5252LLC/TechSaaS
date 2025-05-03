# Billing API Reference

This document describes the TechSaaS Billing API endpoints used for invoice management and billing operations.

## Overview

The Billing API allows you to:

1. **Retrieve current invoice** - Get the invoice for the current billing period
2. **View invoice history** - Access past invoices
3. **Check specific invoices** - Retrieve details for a particular invoice
4. **Get pricing information** - View current pricing for all subscription tiers

All endpoints require authentication via JWT token except for the pricing information endpoint, which is publicly accessible.

## Endpoints

### Get Current Invoice

```
GET /api/v1/billing/invoice
```

Retrieves the current billing period invoice for the authenticated user.

#### Authentication

- Requires a valid JWT token

#### Response

```json
{
  "status": "success",
  "message": "Current billing period invoice",
  "data": {
    "invoice_id": "82d9e881-651b-4c1b-b8a1-d7084ae91e67",
    "user_id": "user123",
    "invoice_date": "2025-05-03",
    "due_date": "2025-06-02",
    "billing_period": {
      "start_date": "2025-05-01",
      "end_date": "2025-05-03"
    },
    "user_info": {
      "name": "John Doe",
      "email": "john@example.com",
      "address": {
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345"
      }
    },
    "subscription_tier": "basic",
    "usage_summary": {
      "requests": 1234,
      "compute_units": 567,
      "tokens": 89012,
      "storage_bytes": 3456789
    },
    "line_items": [
      {
        "description": "Basic Subscription",
        "amount": 9.99,
        "type": "subscription"
      },
      {
        "description": "API Requests (1234)",
        "amount": 1.23,
        "type": "usage"
      },
      {
        "description": "Compute Units (567)",
        "amount": 5.67,
        "type": "usage"
      },
      {
        "description": "Tokens (89012)",
        "amount": 0.89,
        "type": "usage"
      },
      {
        "description": "Storage (3.30 MB)",
        "amount": 0.03,
        "type": "usage"
      }
    ],
    "subtotal": 17.81,
    "total": 17.81,
    "currency": "USD",
    "status": "draft"
  },
  "metadata": {
    "period": {
      "start": "2025-05-01",
      "end": "2025-05-03"
    },
    "generated_at": "2025-05-03T18:30:00.000Z"
  }
}
```

### Get Invoice History

```
GET /api/v1/billing/invoices/history?limit=10
```

Retrieves invoice history for the authenticated user.

#### Authentication

- Requires a valid JWT token

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Maximum number of invoices to return (default: 10, max: 100) |

#### Response

```json
{
  "status": "success",
  "message": "Invoice history (last 3 invoices)",
  "data": [
    {
      "invoice_id": "82d9e881-651b-4c1b-b8a1-d7084ae91e67",
      "invoice_date": "2025-05-03",
      "due_date": "2025-06-02",
      "billing_period": {
        "start_date": "2025-05-01",
        "end_date": "2025-05-03"
      },
      "total": 17.81,
      "status": "draft"
    },
    {
      "invoice_id": "7a1b3c5d-8e7f-4g2h-9i0j-6k5l4m3n2o1p",
      "invoice_date": "2025-04-01",
      "due_date": "2025-05-01",
      "billing_period": {
        "start_date": "2025-04-01",
        "end_date": "2025-04-30"
      },
      "total": 67.23,
      "status": "final"
    },
    {
      "invoice_id": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
      "invoice_date": "2025-03-01",
      "due_date": "2025-04-01",
      "billing_period": {
        "start_date": "2025-03-01",
        "end_date": "2025-03-31"
      },
      "total": 52.47,
      "status": "final"
    }
  ],
  "metadata": {
    "count": 3,
    "generated_at": "2025-05-03T18:30:00.000Z"
  }
}
```

### Get Specific Invoice

```
GET /api/v1/billing/invoice/{invoice_id}
```

Retrieves a specific invoice by ID.

#### Authentication

- Requires a valid JWT token

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| invoice_id | string | ID of the invoice to retrieve |

#### Response

Returns the same response format as the Get Current Invoice endpoint.

### Get Pricing Information

```
GET /api/v1/billing/pricing
```

Retrieves pricing information for all subscription tiers.

#### Authentication

- No authentication required

#### Response

```json
{
  "status": "success",
  "message": "Current pricing information",
  "data": {
    "tiers": {
      "free": {
        "name": "Free",
        "base_fee_monthly": 0,
        "api_request_rate": 0,
        "compute_unit_rate": 0,
        "token_rate": 0,
        "storage_rate": 0,
        "features": [
          "20 requests per minute",
          "1,000 requests per day",
          "Basic AI functionality",
          "Community support"
        ]
      },
      "basic": {
        "name": "Basic",
        "base_fee_monthly": 9.99,
        "api_request_rate": 0.001,
        "compute_unit_rate": 0.01,
        "token_rate": 0.00001,
        "storage_rate": 0.00000001,
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
        "base_fee_monthly": 49.99,
        "api_request_rate": 0.0005,
        "compute_unit_rate": 0.005,
        "token_rate": 0.000005,
        "storage_rate": 0.000000005,
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
        "base_fee_monthly": 199.99,
        "api_request_rate": 0.0002,
        "compute_unit_rate": 0.002,
        "token_rate": 0.000002,
        "storage_rate": 0.000000002,
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
}
```

## Administrative Endpoints

The following endpoints are only accessible to administrators.

### Finalize Invoice

```
POST /api/v1/billing/invoice/{invoice_id}/finalize
```

Finalizes an invoice, changing its status from "draft" to "final".

#### Authentication

- Requires a valid JWT token with admin privileges

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| invoice_id | string | ID of the invoice to finalize |

#### Request Body

```json
{
  "payment_info": {
    "method": "credit_card",
    "reference": "ch_1234567890",
    "date": "2025-05-03T18:30:00.000Z"
  }
}
```

#### Response

Returns the finalized invoice with updated status.

### Generate Invoice for User

```
POST /api/v1/billing/admin/generate-invoice
```

Generates an invoice for a specific user.

#### Authentication

- Requires a valid JWT token with admin privileges

#### Request Body

```json
{
  "user_id": "user123",
  "user_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "CA",
      "zip": "12345"
    }
  },
  "start_date": "2025-04-01",
  "end_date": "2025-04-30",
  "tier": "pro"
}
```

#### Response

Returns the generated invoice.

### Generate Monthly Batch Invoices

```
POST /api/v1/billing/admin/monthly-batch
```

Generates monthly invoices for all users or a specified subset of users.

#### Authentication

- Requires a valid JWT token with admin privileges

#### Request Body

```json
{
  "year": 2025,
  "month": 4,
  "users": [
    "user123",
    "user456"
  ]
}
```

If the users array is empty, invoices will be generated for all users.

#### Response

```json
{
  "status": "success",
  "message": "Generated 2 invoices for 2025-04",
  "data": {
    "success": 2,
    "failed": 0,
    "invoices": [
      {
        "user_id": "user123",
        "invoice_id": "82d9e881-651b-4c1b-b8a1-d7084ae91e67",
        "amount": 67.23
      },
      {
        "user_id": "user456",
        "invoice_id": "7a1b3c5d-8e7f-4g2h-9i0j-6k5l4m3n2o1p",
        "amount": 123.45
      }
    ]
  },
  "metadata": {
    "period": {
      "year": 2025,
      "month": 4,
      "start_date": "2025-04-01",
      "end_date": "2025-04-30"
    },
    "generated_at": "2025-05-03T18:30:00.000Z"
  }
}
```

## Error Responses

### 401 Unauthorized

```json
{
  "status": "error",
  "message": "Authentication required",
  "error": {
    "detail": "Missing or invalid JWT token",
    "status": "unauthorized"
  }
}
```

### 403 Forbidden

```json
{
  "status": "error",
  "message": "Access denied",
  "error": {
    "detail": "You don't have permission to access this resource",
    "status": "forbidden"
  }
}
```

### 404 Not Found

```json
{
  "status": "error",
  "message": "Invoice not found",
  "error": {
    "detail": "No invoice with the specified ID exists",
    "status": "not_found"
  }
}
```

## Rate Limits

The Billing API endpoints are subject to the same rate limits as other API endpoints based on the user's subscription tier.

## Webhooks

Webhook notifications are available for billing events (coming soon):

- `invoice.created` - When a new invoice is generated
- `invoice.finalized` - When an invoice is finalized
- `payment.succeeded` - When a payment is successfully processed
- `payment.failed` - When a payment attempt fails

For information on setting up webhook notifications, see the [Webhook Documentation](webhooks.md).
