# TechSaaS Admin API Guide

**CONFIDENTIAL: FOR AUTHORIZED PERSONNEL ONLY**

This guide explains how to access and use the TechSaaS admin interface. These endpoints give you complete control over the platform, so always maintain strict security practices when using them.

## Authentication

### Development Environment

In development mode, authentication is automatically bypassed to make testing easier. You'll see the admin key printed in the console output when the application starts:

```
======================= DEVELOPMENT MODE =======================
AUTHENTICATION DISABLED FOR DEVELOPMENT
For testing admin access: ADMIN_API_KEY=random_generated_key_here
================================================================
```

Use this key for any admin API requests if you want to test the authentication flow.

### Production Environment

In production, you must authenticate all admin requests with the environment-configured admin key using one of these methods:

**Method 1: X-Admin-Key Header**
```bash
curl -H "X-Admin-Key: your_admin_key_here" https://api.techsaas.app/api/v1/admin/status
```

**Method 2: Bearer Token**
```bash
curl -H "Authorization: Bearer your_admin_key_here" https://api.techsaas.app/api/v1/admin/status
```

## Available Admin Endpoints

### System Status and Configuration

These endpoints give you visibility into the system state:

#### Get System Status
```bash
GET /api/v1/admin/status
```

#### View Current Configuration
```bash
GET /api/v1/admin/config
```

### User Management

Monitor and manage user accounts and subscriptions:

#### List All Users
```bash
GET /api/v1/admin/users
```

Response contains detailed user information including subscription tier, status, and usage statistics.

### Platform Analytics

Monitor platform usage and performance:

#### Usage Statistics
```bash
GET /api/v1/admin/usage/stats?period=day
```

Parameters:
- `period`: `day`, `week`, `month`, or `year`

#### Security Logs
```bash
GET /api/v1/admin/security/logs?level=all&limit=20
```

Parameters:
- `level`: `info`, `warning`, `alert`, or `all`
- `limit`: Number of logs to return (max 100)

### AI Model Management

View and manage available AI models:

#### List Models
```bash
GET /api/v1/admin/models
```

### External API Connectors

Monitor and manage external API integrations:

#### List API Connectors
```bash
GET /api/v1/admin/connectors
```

### Admin Documentation

Access secure documentation within the API:

#### View Documentation Index
```bash
GET /api/v1/admin-docs/
```

#### View Specific Documentation File
```bash
GET /api/v1/admin-docs/file/SECURITY_IMPLEMENTATION.md
```

## Development Testing

For development testing, you can check if authentication bypass is working:

```bash
GET /api/v1/admin/test-auth-override
```

If authentication is bypassed for development, this will return a success status without requiring authentication.

## Security Best Practices

When using admin API access:

1. **Never** share your admin API key
2. Rotate keys regularly (recommended: every 90 days)
3. Use a secure connection (HTTPS) for all admin API requests
4. Keep admin access limited to secure networks
5. Log out and revoke sessions when not in use
6. Monitor security logs for unauthorized access attempts

## Example API Usage

### Example: Check System Status

```bash
# Development environment (authentication optional)
curl http://localhost:5000/api/v1/admin/status

# Production environment (authentication required)
curl -H "X-Admin-Key: your_admin_key_here" https://api.techsaas.app/api/v1/admin/status
```

Expected response:
```json
{
  "timestamp": "2025-05-03T18:25:30.123456",
  "admin_access": true,
  "environment": "development",
  "config_loaded": true,
  "api_version": "1.0.0",
  "server_time": "2025-05-03T18:25:30.123456",
  "auth_mode": "Disabled for Development"
}
```

### Example: View User Information

```bash
# With authentication
curl -H "X-Admin-Key: your_admin_key_here" https://api.techsaas.app/api/v1/admin/users
```

## Troubleshooting

| Error | Possible Cause | Solution |
|-------|----------------|----------|
| 401 Unauthorized | Missing admin API key | Add X-Admin-Key header |
| 403 Forbidden | Invalid admin API key | Check your API key |
| 429 Too Many Requests | Rate limit exceeded | Wait and try again |

Remember that failed admin authentication attempts are logged for security monitoring.

---

*For more details on specific admin features, refer to the other admin documentation files.*
