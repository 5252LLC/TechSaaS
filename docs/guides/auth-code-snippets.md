# JWT Authentication: Implementation Patterns & Code Snippets

This guide provides practical code patterns and ready-to-use snippets for TechSaaS's JWT authentication system.

## Quick Reference

### Client Setup

```python
# Python
import requests

class AuthClient:
    def __init__(self, base_url="https://api.techsaas.tech/v1"):
        self.base_url = base_url
        self.token = None
    
    def set_token(self, token):
        self.token = token
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs.setdefault("headers", {}).update(self.get_headers())
        return requests.request(method, url, **kwargs)
```

```javascript
// JavaScript
class AuthClient {
  constructor(baseUrl = 'https://api.techsaas.tech/v1') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  setToken(token) {
    this.token = token;
  }

  getHeaders() {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }

  async request(method, endpoint, options = {}) {
    const url = `${this.baseUrl}/${endpoint.replace(/^\//, '')}`;
    options.headers = { ...options.headers, ...this.getHeaders() };
    const response = await fetch(url, { method, ...options });
    return response.json();
  }
}
```

## Authentication Patterns

### Token Storage Pattern

```javascript
// Browser - LocalStorage (less secure)
class TokenStorage {
  static saveToken(token) {
    localStorage.setItem('auth_token', token);
  }
  
  static getToken() {
    return localStorage.getItem('auth_token');
  }
  
  static clearToken() {
    localStorage.removeItem('auth_token');
  }
}

// Browser - HttpOnly Cookie (more secure)
// Set on server side with:
// res.cookie('auth_token', token, { httpOnly: true, secure: true });
```

```python
# Server-side token storage (Redis example)
import redis
import uuid

class TokenStorage:
    def __init__(self, redis_url="redis://localhost:6379/0"):
        self.client = redis.from_url(redis_url)
        self.prefix = "token:"
        self.expiry = 1800  # 30 minutes
        
    def save_token(self, user_id, token):
        key = f"{self.prefix}{user_id}"
        self.client.setex(key, self.expiry, token)
        
    def get_token(self, user_id):
        key = f"{self.prefix}{user_id}"
        return self.client.get(key)
    
    def invalidate_token(self, user_id):
        key = f"{self.prefix}{user_id}"
        self.client.delete(key)
```

### Token Refresh Pattern

```javascript
// Auto refresh token when expired
class AuthManager {
  constructor(client) {
    this.client = client;
    this.token = null;
    this.refreshToken = null;
  }

  async login(email, password) {
    const response = await this.client.request('POST', '/auth/login', {
      body: JSON.stringify({ email, password }),
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (response.status === 'success') {
      this.token = response.data.token;
      this.refreshToken = response.data.refresh_token;
      this.client.setToken(this.token);
    }
    
    return response;
  }

  async refreshAccessToken() {
    if (!this.refreshToken) return false;
    
    try {
      const response = await this.client.request('POST', '/auth/refresh', {
        headers: { 'Authorization': `Bearer ${this.refreshToken}` }
      });
      
      if (response.status === 'success') {
        this.token = response.data.token;
        this.refreshToken = response.data.refresh_token;
        this.client.setToken(this.token);
        return true;
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
    }
    
    return false;
  }

  // Handle 401 errors and auto-refresh
  async fetchWithRefresh(fetchFunction) {
    try {
      return await fetchFunction();
    } catch (error) {
      if (error.status === 401) {
        const refreshed = await this.refreshAccessToken();
        if (refreshed) {
          return await fetchFunction();
        }
      }
      throw error;
    }
  }
}
```

## Authorization Patterns

### Role-Based Access Control

```python
# Decorators for RBAC
def requires_role(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return {"error": "Authentication required"}, 401
                
            payload = decode_token(token)
            user_role = payload.get('role', '')
            
            # Role hierarchy check
            role_levels = {
                'user': 0,
                'premium': 1,
                'admin': 2,
                'superadmin': 3
            }
            
            user_level = role_levels.get(user_role, -1)
            required_level = role_levels.get(role, 999)
            
            if user_level >= required_level:
                return func(*args, **kwargs)
            else:
                return {"error": "Insufficient permissions"}, 403
                
        return wrapper
    return decorator

# Usage
@requires_role('admin')
def admin_endpoint():
    return {"message": "Admin access granted"}
```

### Permission-Based Access Control

```python
# Check specific permissions
def has_permission(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return {"error": "Authentication required"}, 401
                
            payload = decode_token(token)
            permissions = payload.get('permissions', [])
            
            if permission in permissions:
                return func(*args, **kwargs)
            else:
                return {
                    "error": "Permission denied",
                    "required_permission": permission
                }, 403
                
        return wrapper
    return decorator

# Check for any of the specified permissions
def has_any_permission(permissions):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return {"error": "Authentication required"}, 401
                
            payload = decode_token(token)
            user_permissions = payload.get('permissions', [])
            
            if any(perm in user_permissions for perm in permissions):
                return func(*args, **kwargs)
            else:
                return {
                    "error": "Permission denied", 
                    "required_permissions": permissions
                }, 403
                
        return wrapper
    return decorator
```

## Feature Access by Subscription Tier

```python
# Check if user's tier has access to a feature
def check_feature_access(feature_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()
            if not token:
                return {"error": "Authentication required"}, 401
                
            payload = decode_token(token)
            user_tier = payload.get('tier', 'free')
            
            # Define which tiers have access to which features
            tier_features = {
                'free_feature': ['free', 'basic', 'premium', 'professional', 'enterprise'],
                'basic_feature': ['basic', 'premium', 'professional', 'enterprise'],
                'premium_feature': ['premium', 'professional', 'enterprise'],
                'pro_feature': ['professional', 'enterprise'],
                'enterprise_feature': ['enterprise']
            }
            
            allowed_tiers = tier_features.get(feature_name, [])
            
            if user_tier in allowed_tiers:
                return func(*args, **kwargs)
            else:
                return {
                    "error": "Feature access denied",
                    "tier": user_tier,
                    "required_tier": allowed_tiers[0] if allowed_tiers else None,
                    "feature": feature_name,
                    "upgrade_url": "https://techsaas.tech/pricing"
                }, 403
                
        return wrapper
    return decorator
```

## API Rate Limiting

```python
# Redis-based rate limiting
import time
import redis
from functools import wraps

class RateLimiter:
    def __init__(self, redis_url="redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url)
        
    def limit_by_tier(self, tier_limits):
        """
        Limit requests by user tier
        
        tier_limits: Dict mapping tiers to requests per minute
        Example: {'free': 10, 'basic': 100, 'premium': 1000}
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                token = get_token_from_request()
                if not token:
                    return func(*args, **kwargs)  # No token, no rate limiting
                    
                payload = decode_token(token)
                user_id = payload.get('sub')
                tier = payload.get('tier', 'free')
                
                # Get the rate limit for this tier
                rpm = tier_limits.get(tier, 10)  # Default to 10 requests per minute
                
                # Check if rate limit exceeded
                key = f"ratelimit:{user_id}:{int(time.time() / 60)}"  # Key expires each minute
                current = self.redis.incr(key)
                self.redis.expire(key, 60)  # Expire after 1 minute
                
                if current > rpm:
                    return {
                        "error": "Rate limit exceeded",
                        "tier": tier,
                        "limit": rpm,
                        "reset_in_seconds": 60 - (int(time.time()) % 60)
                    }, 429
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
```

## API Integration Examples

### Python FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from typing import Optional

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT Configuration
JWT_SECRET = "your-secret-key"
JWT_ALGORITHM = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.get("/user/profile")
def read_user_profile(current_user: dict = Depends(get_current_user)):
    return {"user_id": current_user["sub"], "email": current_user["email"]}

@app.get("/admin/stats")
def admin_stats(current_user: dict = Depends(get_current_user)):
    # Check if user has admin role
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return {"active_users": 1025, "premium_users": 342}
```

### Express.js Integration

```javascript
const express = require('express');
const jwt = require('jsonwebtoken');
const app = express();

// JWT Configuration
const JWT_SECRET = 'your-secret-key';
const JWT_ALGORITHM = 'HS256';

// Authentication middleware
const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      status: 'error',
      message: 'Authentication required',
      error: {
        type: 'authentication_error',
        details: 'No valid authentication token provided'
      }
    });
  }
  
  const token = authHeader.split(' ')[1];
  
  try {
    const decoded = jwt.verify(token, JWT_SECRET, { algorithms: [JWT_ALGORITHM] });
    req.user = decoded;
    next();
  } catch (error) {
    let errorType = 'authentication_error';
    let errorDetails = 'Invalid token';
    
    if (error.name === 'TokenExpiredError') {
      errorType = 'token_expired';
      errorDetails = 'Expired JWT token';
    }
    
    return res.status(401).json({
      status: 'error',
      message: 'Authentication required',
      error: {
        type: errorType,
        details: errorDetails
      }
    });
  }
};

// Role check middleware
const requireRole = (role) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({
        status: 'error',
        message: 'Authentication required'
      });
    }
    
    const roleHierarchy = {
      'user': 0,
      'premium': 1,
      'admin': 2,
      'superadmin': 3
    };
    
    const userRole = req.user.role || 'user';
    const userLevel = roleHierarchy[userRole] || -1;
    const requiredLevel = roleHierarchy[role] || 999;
    
    if (userLevel >= requiredLevel) {
      next();
    } else {
      res.status(403).json({
        status: 'error',
        message: 'Insufficient permissions',
        error: {
          type: 'permission_error',
          details: 'Role access denied',
          userRole,
          requiredRole: role
        }
      });
    }
  };
};

// Protected route example
app.get('/user/profile', authenticate, (req, res) => {
  res.json({
    status: 'success',
    data: {
      id: req.user.sub,
      email: req.user.email,
      role: req.user.role,
      tier: req.user.tier
    }
  });
});

// Role-protected route example
app.get('/admin/dashboard', authenticate, requireRole('admin'), (req, res) => {
  res.json({
    status: 'success',
    data: {
      stats: {
        users: 1025,
        revenue: 54280
      }
    }
  });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

## Error Handling Patterns

```javascript
// Error handling middleware for Express
const errorHandler = (err, req, res, next) => {
  // Default error
  let statusCode = err.statusCode || 500;
  let message = err.message || 'Internal Server Error';
  let errorType = err.type || 'server_error';
  let errorDetails = err.details || err.message;
  
  // JWT errors
  if (err.name === 'JsonWebTokenError') {
    statusCode = 401;
    errorType = 'authentication_error';
    message = 'Authentication required';
    errorDetails = 'Invalid token';
  } else if (err.name === 'TokenExpiredError') {
    statusCode = 401;
    errorType = 'token_expired';
    message = 'Authentication required';
    errorDetails = 'Expired JWT token';
  }
  
  res.status(statusCode).json({
    status: 'error',
    message,
    error: {
      type: errorType,
      details: errorDetails
    },
    metadata: {
      timestamp: Date.now()
    }
  });
};

// Usage
app.use(errorHandler);
```

## Testing Authentication

```python
# PyTest example for testing authentication
import pytest
import jwt
import time

def generate_test_token(user_id, role='user', tier='free', exp_minutes=30):
    """Generate a test JWT token"""
    now = int(time.time())
    payload = {
        'sub': user_id,
        'email': f'test.{role}@example.com',
        'role': role,
        'tier': tier,
        'iat': now,
        'exp': now + (exp_minutes * 60)
    }
    return jwt.encode(payload, 'test-secret', algorithm='HS256')

@pytest.fixture
def user_token():
    return generate_test_token('test-user-123')

@pytest.fixture
def admin_token():
    return generate_test_token('test-admin-123', role='admin', tier='professional')

def test_user_access(client, user_token):
    response = client.get(
        '/user/profile',
        headers={'Authorization': f'Bearer {user_token}'}
    )
    assert response.status_code == 200
    assert response.json()['data']['id'] == 'test-user-123'

def test_admin_access_denied(client, user_token):
    response = client.get(
        '/admin/dashboard',
        headers={'Authorization': f'Bearer {user_token}'}
    )
    assert response.status_code == 403
    assert response.json()['error']['type'] == 'permission_error'

def test_admin_access_allowed(client, admin_token):
    response = client.get(
        '/admin/dashboard',
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert response.status_code == 200
```

## Deployment Considerations

### Environment Variables

```
# .env file for production
JWT_SECRET=your-secure-random-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=30m
JWT_REFRESH_EXPIRES_IN=7d
REDIS_URL=redis://redis:6379/0
```

### Docker Configuration

```yaml
# docker-compose.yml
version: '3'

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - JWT_ALGORITHM=${JWT_ALGORITHM}
      - JWT_EXPIRES_IN=${JWT_EXPIRES_IN}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

## Security Best Practices

1. Store JWTs in HttpOnly cookies (for web) or secure storage (for mobile)
2. Use short expiration times (30-60 minutes) for access tokens
3. Implement refresh token rotation
4. Set proper CORS headers and CSP policies
5. Use HTTPS in all environments, including development
6. Implement rate limiting to prevent brute force attacks
7. Add audit logging for all authentication and authorization events
