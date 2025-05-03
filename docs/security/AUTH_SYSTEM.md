# TechSaaS JWT Authentication & Authorization System

## Overview

This document provides a comprehensive guide to the security layer implemented in the TechSaaS platform. The system uses JWT (JSON Web Tokens) for authentication, combined with role-based access control (RBAC) and tier-based authorization to secure API endpoints based on user roles and subscription levels.

## Architecture

The security system consists of three main components:

1. **JWT Authentication Middleware** (`security.py`): Validates JWT tokens and enforces security headers
2. **Authorization Middleware** (`authorization.py`): Provides tier-based access control and permission checking
3. **Role-Based Access Control** (`rbac.py`): Implements role hierarchy and role-based authorization

### Authentication Flow

```
┌──────────┐      1. Login Request     ┌──────────┐
│          │ ─────────────────────────>│          │
│  Client  │                           │   API    │
│          │ <─────────────────────────│  Server  │
└──────────┘     2. JWT Token          └──────────┘
     │                                       ▲
     │                                       │
     │ 3. Requests with                      │
     │    Bearer Token                       │
     │                                       │
     │                                       │
     ▼                                       │
┌──────────┐      4. Protected       ┌──────────┐
│ Security │      Resources          │  Route   │
│Middleware│ ─────────────────────────> Handler │
└──────────┘                         └──────────┘
```

## JWT Token Structure

```json
{
  "sub": "user-id-123",
  "email": "user@example.com",
  "role": "user|premium|admin|superadmin",
  "tier": "free|basic|premium|professional|enterprise",
  "iat": 1746311019,
  "exp": 1746312819
}
```

## Core Components

### 1. Security Middleware (security.py)

The security middleware is responsible for:

- JWT token validation
- Token expiration checking
- Security headers management
- Token extraction from request headers

Key functions:
- `validate_jwt(token)`: Validates and decodes JWT tokens
- `get_token_from_header(request)`: Extracts JWT token from Authorization header
- `jwt_required()`: Decorator for endpoints requiring authentication

### 2. Authorization Middleware (authorization.py)

The authorization middleware handles:

- Tier-based access control
- Permission-based authorization
- API resource protection

Key decorators:
- `requires_tier(tier_name)`: Restricts endpoint to specific subscription tiers
- `has_permission(permission)`: Checks if user has specific permission
- `has_any_permission(permissions)`: Checks if user has any of the listed permissions
- `has_all_permissions(permissions)`: Checks if user has all listed permissions

### 3. Role-Based Access Control (rbac.py)

The RBAC component implements:

- Role hierarchy (inheritance)
- Role-permission mapping
- Role validation

Role hierarchy:
```
superadmin
    ├── admin
    │     └── premium
    │           └── user
    └── developer
```

## Usage Examples

### Protecting an Endpoint with Authentication

```python
from api.v1.middleware.security import jwt_required

@app.route('/api/v1/protected/resource')
@jwt_required()
def protected_resource():
    # Only authenticated users can access this endpoint
    return jsonify({"message": "This is a protected resource"})
```

### Tier-Based Access Control

```python
from api.v1.middleware.authorization import requires_tier

@app.route('/api/v1/premium-feature')
@jwt_required()
@requires_tier('premium')
def premium_feature():
    # Only premium tier and above can access this endpoint
    return jsonify({"message": "This is a premium feature"})
```

### Role-Based Access Control

```python
from api.v1.middleware.rbac import requires_role

@app.route('/api/v1/admin/dashboard')
@jwt_required()
@requires_role('admin')
def admin_dashboard():
    # Only admin and above can access this endpoint
    return jsonify({"message": "Admin dashboard"})
```

### Permission-Based Access Control

```python
from api.v1.middleware.authorization import has_permission

@app.route('/api/v1/analytics/report')
@jwt_required()
@has_permission('view_analytics')
def analytics_report():
    # Only users with 'view_analytics' permission can access this
    return jsonify({"message": "Analytics report"})
```

## Testing Utilities

### Token Generator (token_generator.py)

Utility for generating test tokens with different roles and tiers.

```python
from api.v1.utils.token_generator import generate_test_token

# Generate a token for a premium user
token = generate_test_token(
    user_id="test-user-123",
    email="premium@example.com",
    role="premium",
    tier="premium",
    expires_in_minutes=30
)
```

### Debug Utility (debug_token.py)

Standalone script for debugging JWT tokens outside of the Flask application:

```bash
# Generate a new test token
python debug_token.py generate

# Verify an existing token
python debug_token.py <token>
```

## API Response Format

All security-related responses follow the standard response format:

```json
{
  "status": "error",
  "message": "Unauthorized access",
  "error": {
    "type": "authentication_error",
    "details": "Invalid or expired token"
  },
  "metadata": {
    "timestamp": 1746311026.5279362
  }
}
```

## Configuration Settings

The following environment variables can be used to configure the JWT security system:

| Variable | Description | Default |
|----------|-------------|---------|
| JWT_SECRET_KEY | Secret key for signing tokens | "development-secret-key-change-in-production" |
| JWT_ALGORITHM | Algorithm for token signing | "HS256" |
| JWT_ACCESS_TOKEN_EXPIRES | Access token expiry (minutes) | 30 |
| JWT_REFRESH_TOKEN_EXPIRES | Refresh token expiry (days) | 30 |

## Security Best Practices

1. **Always use HTTPS** in production to prevent token interception
2. **Set appropriate token expiration times** (short for access tokens, longer for refresh tokens)
3. **Use a strong, unique JWT_SECRET_KEY** in production
4. **Implement token blacklisting** for logout and compromised tokens
5. **Validate all user inputs** before processing
6. **Apply the principle of least privilege** when assigning roles and permissions

## Known Limitations

1. JWT tokens cannot be forcibly invalidated before expiration without implementing a token blacklist
2. Stateless authentication requires additional measures for handling user logout
3. RBAC system may require more granular permissions for complex authorization scenarios

## Roadmap

1. Implement Redis-based token blacklist for better scalability
2. Add more granular permission control
3. Implement API key-based authentication for machine-to-machine communication
4. Add brute force prevention with rate limiting on authentication endpoints
5. Implement CSRF protection for browser-based clients

## Troubleshooting

### Common Issues and Solutions

1. **"Token not yet valid" error**
   - The server and client clocks might be out of sync
   - Solution: Use integer timestamps instead of floating-point to avoid precision issues

2. **"Authentication required" error**
   - The Authorization header is missing or malformed
   - Solution: Ensure the token is included in the format: `Authorization: Bearer <token>`

3. **"Token expired" error**
   - The token has exceeded its expiration time
   - Solution: Implement token refresh to obtain a new token
