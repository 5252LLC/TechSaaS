# TechSaaS Security Middleware

## Overview

This directory contains the security middleware components for the TechSaaS platform. These components provide JWT-based authentication, role-based access control (RBAC), and tier-based authorization capabilities.

## Components

### 1. Security Middleware (`security.py`)

Core JWT authentication middleware that:
- Validates JWT tokens
- Enforces security headers
- Handles token extraction from request headers
- Provides JWT-related decorators

### 2. Authorization Middleware (`authorization.py`)

Handles permission and tier-based access control:
- Tier validation for subscription-based features
- Permission-based access control decorators
- Resource ownership validation

### 3. RBAC Middleware (`rbac.py`)

Implements role-based access control:
- Role hierarchy and inheritance
- Role validation
- Role-specific permission management

## Usage

Apply these middleware components using decorators on your route handlers:

```python
from api.v1.middleware.security import jwt_required
from api.v1.middleware.authorization import requires_tier, has_permission
from api.v1.middleware.rbac import requires_role

@app.route('/api/v1/protected-endpoint')
@jwt_required()
@requires_role('admin')
@requires_tier('premium')
@has_permission('manage_users')
def protected_endpoint():
    # Only authenticated admin users with premium tier 
    # and 'manage_users' permission can access this endpoint
    return jsonify({"message": "Protected endpoint"})
```

## Testing

Use the token generation utilities in `/api/v1/utils/token_generator.py` to generate test tokens with different roles and tiers.

## Documentation

For comprehensive documentation, please see:
- [AUTH_SYSTEM.md](/docs/security/AUTH_SYSTEM.md) - Full documentation of the authentication system
- [API_SECURITY.md](/docs/api/API_SECURITY.md) - API security guidelines and best practices

## Configuration

Security settings can be configured through environment variables:
- `JWT_SECRET_KEY` - Secret key for signing tokens
- `JWT_ALGORITHM` - Algorithm for token signing (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRES` - Access token expiry in minutes
