# TechSaaS API Key Management System

![TechSaaS Logo](../../web-interface/static/images/techsaas-logo.png)

## Overview

The TechSaaS API Key Management system provides secure creation, validation, and management of API keys with comprehensive audit trail integration. This system is a critical security component, allowing for controlled access to your TechSaaS APIs while maintaining detailed audit logs for compliance purposes.

---

## 🚀 Getting Started (Beginner-Friendly)

### What Are API Keys?

API keys are secure tokens that allow external developers or services to authenticate with your TechSaaS APIs. Unlike user accounts, API keys:
- Are designed for machine-to-machine communication
- Can have precise permission scopes
- Can be easily revoked without affecting user accounts
- Support usage tracking and rate limiting

### Key Security Features

- **Tamper-evident audit logging**: Every API key operation (creation, validation, revocation) is logged to the immutable audit trail
- **Tiered access levels**: Support for basic, premium, and enterprise tiers with different rate limits
- **Secure storage**: API key secrets are never stored in plaintext (only hashed)
- **Expiration dates**: Keys automatically expire based on subscription tier
- **Scope-based permissions**: Fine-grained access control for API operations

### Creating Your First API Key

1. **Log in to your TechSaaS account**
2. **Navigate to Settings > API Keys**
3. **Click "Create New API Key"**
4. **Configure the key settings:**
   - Provide a descriptive name
   - Select the appropriate tier
   - Choose the required permission scopes
5. **Click "Generate Key"**
6. **Copy and securely store your API key immediately**
   - This is the only time the complete key will be displayed

#### Using API Keys in Requests

```bash
# Using an API key in a curl request
curl -X GET "https://api.techsaas.tech/api/v1/data" \
  -H "X-API-Key: tsk.5e8f8c1d-1234-abcd-ef56-789012345678.a1b2c3d4e5f6a7b8c9d0"
  
# Alternatively, you can use a Bearer token format
curl -X GET "https://api.techsaas.tech/api/v1/data" \
  -H "Authorization: Bearer tsk.5e8f8c1d-1234-abcd-ef56-789012345678.a1b2c3d4e5f6a7b8c9d0"
```

### Managing Your API Keys

- **Viewing Keys**: See all your active API keys in Settings > API Keys
- **Revoking Keys**: Click the "Revoke" button next to any key you want to disable
- **Checking Usage**: View usage statistics for each key in the dashboard

---

## 💻 Quick Reference for Experienced Developers

### API Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/apikeys/` | POST | Create a new API key |
| `/api/v1/apikeys/` | GET | List all API keys for the authenticated user |
| `/api/v1/apikeys/<key_id>` | DELETE | Revoke an API key |
| `/api/v1/apikeys/verify` | POST | Verify an API key and show its metadata |
| `/api/v1/apikeys/info/<key_id>` | GET | Admin only: Get detailed information about an API key |

### API Key Manager Methods

```python
# Key API Key Manager methods
from api.v1.utils.api_key_manager import ApiKeyManager

key_manager = ApiKeyManager()

# Create a key
key_data = key_manager.create_key(user_id, tier, name, scopes)

# Validate a key 
is_valid, key_info = key_manager.validate_key(api_key)

# Revoke a key
success = key_manager.revoke_key(user_id, key_id)

# Get a user's keys
keys = key_manager.get_user_keys(user_id)
```

### API Key Authentication Decorator

```python
# Protecting an endpoint with API key authentication
from api.v1.utils.api_key_manager import api_key_auth
from flask import Blueprint, g

api_bp = Blueprint("api", __name__)

@api_bp.route("/private-data", methods=["GET"])
@api_key_auth(required_scopes=["read"])
def get_private_data():
    # The API key details are available in g.api_key
    user_id = g.user_id
    api_tier = g.api_tier
    
    # Your protected API logic here
    return {"data": "This is protected data", "tier": api_tier}
```

### Request Examples

```python
# Python requests example
import requests

url = "https://api.techsaas.tech/api/v1/data"
headers = {
    "X-API-Key": "tsk.5e8f8c1d-1234-abcd-ef56-789012345678.a1b2c3d4e5f6a7b8c9d0"
}

response = requests.get(url, headers=headers)
print(response.json())
```

```javascript
// JavaScript fetch example
const url = "https://api.techsaas.tech/api/v1/data";
const options = {
  method: "GET",
  headers: {
    "X-API-Key": "tsk.5e8f8c1d-1234-abcd-ef56-789012345678.a1b2c3d4e5f6a7b8c9d0"
  }
};

fetch(url, options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

---

## 📚 Professional Documentation

### Architecture

The API Key Management system is built on the following architectural principles:

1. **Security**: Protection against common attack vectors
2. **Auditability**: Complete logging of all key operations
3. **Performance**: Optimized database queries and caching
4. **Compliance**: Support for regulatory requirements
5. **Scalability**: Distribution-friendly design

### API Key Format and Structure

TechSaaS API keys follow a three-part format: `prefix.id.secret`

- **Prefix**: Always `tsk` (TechSaaS Key)
- **ID**: A UUID identifying the key in the database
- **Secret**: A high-entropy (192 bits) random value

This structure allows for easy key validation and revocation while maintaining security.

### Database Schema

The API key system uses two tables:

1. **`api_keys`**: Stores API key metadata and hashed secrets
    - `id`: UUID identifying the key
    - `user_id`: ID of the key owner
    - `name`: Friendly name for the key
    - `secret_hash`: Hashed version of the key secret
    - `tier`: Subscription tier (basic, premium, enterprise)
    - `rate_limit`: Requests per minute allowed
    - `scopes`: Comma-separated list of permissions
    - `created_at`: Creation timestamp
    - `expires_at`: Expiration timestamp
    - `last_used_at`: Last usage timestamp
    - `revoked_at`: Revocation timestamp
    - `is_enabled`: Whether the key is active

2. **`api_key_usage`**: Tracks API key usage for billing and auditing
    - `id`: UUID for the usage record
    - `api_key_id`: Foreign key to the API key
    - `endpoint`: API endpoint accessed
    - `method`: HTTP method used
    - `status_code`: HTTP status returned
    - `response_time`: Request processing time
    - `request_size`: Size of request in bytes
    - `response_size`: Size of response in bytes
    - `ip_address`: Client IP address
    - `timestamp`: When the request occurred

### Tier-Based Rate Limiting

| Tier | Rate Limit (requests/minute) | Expiration | Description |
|------|------------------------------|------------|-------------|
| Basic | 60 | 1 year | Suitable for individual developers and testing |
| Premium | 300 | 2 years | For small to medium businesses |
| Enterprise | 1200 | 3 years | For high-volume applications |

### Audit Trail Integration

Every significant API key operation is logged to the audit trail with appropriate sensitivity levels:

- **API Key Creation** (SENSITIVITY_HIGH)
- **API Key Validation** (SENSITIVITY_MEDIUM)
- **API Key Revocation** (SENSITIVITY_HIGH)
- **Failed Key Attempts** (SENSITIVITY_HIGH)
- **Admin API Key Access** (SENSITIVITY_HIGH)

Example audit events:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-05-04T12:34:56.789Z",
  "event_type": "api_key_management",
  "action": "create",
  "actor_id": "user-123",
  "actor_type": "user",
  "resource_type": "api_key",
  "resource_id": "5e8f8c1d-1234-abcd-ef56-789012345678",
  "outcome": "success",
  "details": {
    "name": "Production API Key",
    "tier": "enterprise",
    "scopes": ["read", "write", "admin"]
  },
  "sensitivity": "high"
}
```

### Security Considerations

1. **Secure Storage**: API key secrets are never stored in plaintext, only secure hashes
2. **Tamper Evidence**: All key operations are logged in the tamper-evident audit trail
3. **Authorization**: Users can only manage their own API keys
4. **Rate Limiting**: Protection against brute force attacks
5. **Key Expiration**: Automatic expiration based on subscription tier

---

## ⚙️ Advanced Usage and Best Practices

### Testing API Keys

Before deploying to production, verify your API key works correctly:

```python
# Test an API key with the verify endpoint
import requests

response = requests.post(
    "https://api.techsaas.tech/api/v1/apikeys/verify",
    headers={"X-API-Key": "your-api-key"}
)

if response.status_code == 200:
    print("API key is valid")
    print(f"Key details: {response.json()['data']}")
else:
    print("API key is invalid")
```

### Implementing API Key Rotation

For optimal security, periodically rotate your API keys:

1. Create a new API key with the same permissions
2. Update your applications to use the new key
3. Verify the new key works correctly
4. Revoke the old key

### Checking API Key Audit Logs

As an administrator, you can inspect API key audit logs:

```python
# Query the audit trail for API key events
from api.v1.utils.audit_trail import get_audit_trail

audit_trail = get_audit_trail()
events = audit_trail.query_events(
    event_type="api_key_management",
    resource_id="your-key-id",
    limit=10
)

for event in events:
    print(f"{event.timestamp}: {event.action} - {event.outcome}")
    print(f"Details: {event.details}")
```

### Environment-Specific Key Management

Best practices for different environments:

**Development**:
- Use separate development API keys
- Lower rate limits and shorter expirations
- Broader scopes for easier testing

**Staging**:
- Mirror production key configurations
- Use realistic rate limits
- Test key expiration and rotation

**Production**:
- Apply the principle of least privilege
- Use precise permission scopes
- Implement strict key rotation policies
- Monitor usage patterns for anomalies

---

## 🔒 Is My Entire App Protected?

The API key management system is designed to work alongside our existing JWT-based authentication and role-based access controls. Together, these systems provide comprehensive protection for the TechSaaS platform:

1. **User Authentication**: Protected by JWT tokens and robust password policies
2. **API Authentication**: Protected by API keys with scope-based permissions
3. **Access Control**: Protected by role-based and permission-based checks
4. **Audit Trail**: All security events are logged with tamper evidence
5. **Rate Limiting**: Protection against abuse and DoS attacks

To secure your entire application, ensure you:

1. Apply the `@token_required` decorator to user-facing endpoints
2. Apply the `@api_key_auth()` decorator to API endpoints
3. Implement proper permission checks with `@has_permission()`
4. Log security-relevant events to the audit trail
5. Regularly review the audit logs for suspicious activity

By following these practices, your TechSaaS application will maintain a strong security posture that meets regulatory requirements.

## Compliance Benefits

The API key management system with audit trail integration helps meet requirements for:

- **SOC2**: Providing logical access controls and monitoring
- **HIPAA**: Supporting authorization controls and audit logging
- **GDPR**: Enabling accountability and access management
- **PCI-DSS**: Maintaining secure authentication and audit trails

## Troubleshooting Common Issues

| Issue | Possible Causes | Solutions |
|-------|----------------|-----------|
| "Invalid API key" | Key revoked, expired, or mistyped | Verify key format, check expiration, generate new key if needed |
| "Insufficient scopes" | Key missing required permissions | Create new key with correct scopes |
| "Rate limit exceeded" | Too many requests for tier | Upgrade tier or optimize request patterns |
| "API key not found" | Key ID doesn't exist | Check for typos, generate new key |
| "Unauthorized key access" | Attempting to manage another user's key | Verify user identity and permissions |

## Additional Resources

- [API Security Best Practices](../api/API_SECURITY.md)
- [TechSaaS Authentication Guide](../guides/auth-beginners-guide.md)
- [Rate Limiting Documentation](../api/rate-limiting.md)
- [Audit Trail System](../guides/audit-trail.md)
