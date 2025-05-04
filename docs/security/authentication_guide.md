# TechSaaS Authentication Security Guide

This guide explains how the TechSaaS platform handles authentication and security, from basic concepts to advanced implementation details.

## 🔰 For Beginners: Understanding Authentication in TechSaaS

### What is Authentication?

Authentication is how our system verifies that you are who you say you are. Think of it like showing your ID card at a secure building.

### How TechSaaS Authentication Works

1. **Sign Up**: You create an account with your email and password
2. **Login**: You enter these credentials to get access
3. **Security Token**: The system gives you a special digital "access card" (JWT token)
4. **Using the Token**: You show this token each time you want to use a protected feature

### What Makes Our System Secure?

- **Password Protection**: Your password is never stored as plain text
- **Secure Tokens**: Special digital passes that expire automatically
- **Multiple Security Layers**: Several checks to make sure you are authorized

## 👨‍💻 For Experienced Developers: Implementation Quick Guide

### JWT Authentication Implementation

```javascript
// Client-side authentication call
async function login(email, password) {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  if (data.access_token) {
    // Store tokens securely
    localStorage.setItem('access_token', data.access_token);
    return true;
  }
  return false;
}

// Making authenticated API calls
async function fetchProtectedResource() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/api/v1/protected/resource', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
}
```

### Role-Based Access Control

```python
# Python decorator example for role-based protection
@jwt_required
@has_permission('admin:view')
def admin_dashboard():
    """Admin endpoint - requires admin role"""
    return ResponseFormatter.success_response(
        message="Admin dashboard accessed",
        data={"role": g.user.get('role')}
    )
```

### Quick Implementation Steps

1. Configure JWT settings in your `.env` file (see `.env.example`)
2. Use the middleware for protected routes
3. Check user permissions with the role/permission decorators
4. Handle token refresh for long-lived sessions

## 🛡️ For Security Professionals: Detailed Implementation

### Authentication Security Architecture

TechSaaS implements a comprehensive JWT-based authentication system with multiple layers of security:

1. **Token Generation & Validation**: Cryptographically signed tokens with proper claim validation
2. **Role Hierarchy Enforcement**: Strictly enforced role hierarchy prevents privilege escalation
3. **Token Blacklisting**: Revocation mechanism for compromised or expired tokens
4. **Audit Trail**: Comprehensive logging of all authentication events
5. **Timezone-aware Token Handling**: Prevents timing attacks related to token expiration

### JWT Implementation Details

```python
def verify_jwt_token(token, required_type='access'):
    """
    Verify JWT token and return payload if valid
    
    Args:
        token: JWT token to verify
        required_type: Required token type ('access' or 'refresh')
        
    Returns:
        dict or None: Token payload if valid, None if invalid
    """
    if not token or not isinstance(token, str):
        return None
        
    # Check if token is in the expected format (3 parts separated by dots)
    if token.count('.') != 2:
        logger.warning("JWT token has incorrect format")
        return None
        
    # Check if token is blacklisted
    if token in token_blacklist:
        logger.warning("Token is blacklisted")
        return None
    
    try:
        # Decode token with strict verification
        payload = jwt.decode(
            token, 
            JWT_SECRET_KEY, 
            algorithms=[JWT_ALGORITHM],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_iat': True,
                'require': ['exp', 'iat', 'sub', 'type']
            }
        )
        
        # Check if token ID is blacklisted
        if 'jti' in payload and payload['jti'] in token_blacklist:
            logger.warning(f"Token with blacklisted JTI {payload['jti']} rejected")
            return None
        
        # Verify token type
        if payload.get('type') != required_type:
            logger.warning(f"Token type mismatch: expected {required_type}, got {payload.get('type')}")
            return None
            
        # Additional validation for access tokens
        if required_type == 'access':
            if 'role' not in payload:
                logger.warning("Access token missing role field")
                return None
                
            if 'tier' not in payload:
                logger.warning("Access token missing tier field")
                return None
            
            # Validate role is a known role
            if payload.get('role') not in ROLE_HIERARCHY:
                logger.warning(f"Invalid role in token: {payload.get('role')}")
                return None
            
            # Validate tier is a known tier
            if payload.get('tier') not in TIER_PERMISSIONS:
                logger.warning(f"Invalid tier in token: {payload.get('tier')}")
                return None
        
        # Log successful token verification
        logger.debug(f"Token verified successfully: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.info("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        return None
```

### Security Vulnerabilities Prevented

1. **Authentication Bypass**: Multiple layers of token validation prevent bypass attacks
2. **Vertical Privilege Escalation**: Strict role hierarchy validation prevents role escalation
3. **Token Replay**: JWT IDs (jti) and token blacklisting prevent token reuse
4. **Timing Attacks**: UTC timezone standardization prevents expiration-related timing issues
5. **Token Tampering**: Cryptographic signature verification detects manipulated tokens

### Environment Configuration

For proper security in production environments, configure these settings:

```ini
# JWT Security (IMPORTANT: Generate a strong random key for production)
JWT_SECRET_KEY=generate-a-strong-random-key-for-production
JWT_ACCESS_TOKEN_EXPIRES=30  # minutes
JWT_REFRESH_TOKEN_EXPIRES=7  # days
JWT_ALGORITHM=HS256
```

### Security Testing

We've implemented comprehensive security testing for the authentication system:

```python
# Token validation test example
def test_tampered_role_escalation(self):
    """Test that tokens with tampered roles for privilege escalation are rejected"""
    # Create admin token with the wrong signature
    admin_payload = self.valid_payload.copy()
    admin_payload['role'] = 'admin'
    
    # Encode with a wrong key (simulating a tampered token)
    tampered_token = jwt.encode(
        admin_payload,
        'fake-secret-for-tampering',
        algorithm=JWT_ALGORITHM
    )
    
    result = verify_jwt_token(tampered_token)
    self.assertIsNone(result, "Tampered token for privilege escalation was accepted")
```

## Best Practices

1. **Never hardcode secrets** in your source code
2. **Use environment variables** for sensitive configuration
3. **Set appropriate token expiration** times
4. **Implement token refresh** for better user experience
5. **Log security events** for audit and compliance
6. **Test token validation** thoroughly
7. **Use HTTPS** for all authentication traffic
8. **Implement rate limiting** to prevent brute force attacks

## API Reference

### Authentication Endpoints

| Endpoint | Method | Description | Request Body | Response |
|----------|--------|-------------|--------------|----------|
| `/api/v1/auth/register` | POST | Register a new user | `{email, password, name}` | `{access_token, refresh_token}` |
| `/api/v1/auth/login` | POST | Login a user | `{email, password}` | `{access_token, refresh_token}` |
| `/api/v1/auth/refresh` | POST | Refresh access token | `{refresh_token}` | `{access_token}` |
| `/api/v1/auth/logout` | POST | Logout (blacklist token) | None | `{message}` |

### Decorators for Protected Routes

| Decorator | Description | Example |
|-----------|-------------|---------|
| `@jwt_required` | Requires valid JWT token | `@jwt_required` |
| `@has_permission(permission)` | Requires specific permission | `@has_permission('admin:view')` |
| `@role_required(role)` | Requires specific role | `@role_required('admin')` |
| `@tier_required(tier)` | Requires subscription tier | `@tier_required('premium')` |

## Need Help?

- **Beginners**: Check out our [Getting Started Guide](/docs/guides/getting-started.md)
- **Developers**: Join our [Discord community](https://discord.gg/techsaas) for quick answers
- **Security issues**: Report through our [security portal](https://techsaas.tech/security)
