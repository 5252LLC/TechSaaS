# TechSaaS API Security Guide

## Overview

This document provides guidelines and best practices for securely interacting with the TechSaaS API. Our authentication system uses JWT (JSON Web Tokens) for authentication and includes role-based and tier-based access controls.

## Authentication

### Obtaining a JWT Token

To authenticate with the TechSaaS API, you need to obtain a JWT token by making a request to the login endpoint:

```bash
curl -X POST http://api.techsaas.tech/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'
```

The response will include your JWT token:

```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "123",
      "email": "your-email@example.com",
      "role": "user",
      "tier": "basic"
    }
  },
  "metadata": {
    "token_expires_in": 1800
  }
}
```

### Using the JWT Token

To access protected resources, include the JWT token in your request's Authorization header:

```bash
curl -X GET http://api.techsaas.tech/api/v1/protected/resource \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration and Refresh

Access tokens expire after 30 minutes by default. To obtain a new access token, use your refresh token:

```bash
curl -X POST http://api.techsaas.tech/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

## Subscription Tiers and Access Control

The TechSaaS API provides different levels of access based on your subscription tier:

| Tier | Features Available | Rate Limits |
|------|-------------------|-------------|
| Free | Basic text analysis, simple image processing | 50 requests/minute |
| Basic | Enhanced text analysis, image recognition | 100 requests/minute |
| Premium | Advanced AI models, audio processing | 500 requests/minute |
| Professional | Multimodal processing, custom model tuning | 1000 requests/minute |
| Enterprise | Full platform access, specialized models | Customizable |

When you attempt to access features not included in your subscription tier, you'll receive a 403 Forbidden response with information about upgrading:

```json
{
  "status": "error",
  "message": "This endpoint requires a premium subscription",
  "error": {
    "type": "insufficient_tier",
    "details": "Your current tier (basic) does not have access to this resource"
  },
  "metadata": {
    "upgrade_url": "https://techsaas.tech/pricing",
    "required_tier": "premium"
  }
}
```

## Error Handling

The API uses consistent error responses:

```json
{
  "status": "error",
  "message": "Error message goes here",
  "error": {
    "type": "error_type",
    "details": "Additional error details"
  },
  "metadata": {
    "timestamp": 1746311026.5279362
  }
}
```

Common authentication-related error types:

| Error Type | Description | HTTP Status Code |
|------------|-------------|------------------|
| `authentication_required` | No token provided | 401 |
| `token_expired` | Token has expired | 401 |
| `token_invalid` | Invalid token format or signature | 401 |
| `insufficient_permissions` | Missing required permissions | 403 |
| `insufficient_tier` | Subscription tier too low | 403 |
| `role_required` | User role insufficient | 403 |

## Security Best Practices

### Client-Side Security

1. **Never store tokens in local storage** - They are vulnerable to XSS attacks
2. **Use HttpOnly cookies** for web applications when possible
3. **Implement token refresh** to handle expiring tokens
4. **Set appropriate token expiration** - Short lifetimes for access tokens
5. **Transport tokens over HTTPS only**

### API Request Security

1. **Validate all user inputs** before sending to the API
2. **Sanitize API responses** before rendering in your application
3. **Implement proper error handling** for authentication failures
4. **Never expose tokens in URLs** - Use headers or POST body
5. **Use limited-scope tokens** when possible

### Token Management

1. **Implement secure logout** by clearing tokens
2. **Detect and handle token expiration** gracefully
3. **Don't share tokens** between different applications
4. **Invalidate tokens** when users change passwords or on suspected breach
5. **Monitor and audit token usage** for suspicious activity

## Testing the API

For testing purposes, you can use our token generation endpoint:

```bash
# Generate a token for testing (development environments only)
curl http://localhost:5552/api/v1/token-test/generate/user/basic
```

## Troubleshooting

### Common Issues

1. **"Invalid token" errors**
   - Check that your token is valid and properly formatted
   - Ensure you're using the correct JWT_SECRET_KEY

2. **"Token expired" errors**
   - Your token has expired and needs to be refreshed
   - Implement proper token refresh handling in your client

3. **"Insufficient permissions" errors**
   - Your user account doesn't have the required permissions
   - Check the required permissions in the API documentation

### Contact Support

If you encounter persistent authentication issues, please contact our developer support:
- Email: api-support@techsaas.tech
- Developer Forum: https://developers.techsaas.tech/forum
- Status Page: https://status.techsaas.tech
