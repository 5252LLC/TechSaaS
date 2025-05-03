# TechSaaS Admin Documentation

**CONFIDENTIAL: FOR AUTHORIZED PERSONNEL ONLY**

This documentation contains sensitive information about TechSaaS administration, security implementation, and system architecture. Access should be restricted to authorized administrators only.

## Authentication Details

### Admin Authentication

The platform uses a secure authentication system for admin access:

1. **API Key Authentication**
   - Set via the `ADMIN_API_KEY` environment variable
   - Must be at least 32 characters in production
   - For development, a random secure token is automatically generated
   - Keys are validated using constant-time comparison to prevent timing attacks

2. **Development Mode**
   - `DISABLE_AUTH_FOR_DEV` setting enables bypass during local development
   - NEVER enabled in production environment
   - Auto-disabled when `AI_SERVICE_ENV=production`

3. **Security Measures**
   - Rate limiting: 5 attempts per minute from the same IP
   - Constant-time comparison to prevent timing attacks
   - Comprehensive logging of all authentication attempts
   - IP tracking for suspicious activity

### API Key Management

Admin API keys should be:
- Stored securely in a password manager
- Rotated every 90 days
- Never shared with unauthorized personnel
- Never committed to version control

## Admin API Access

Admin endpoints are available at `/api/v1/admin/*` and include:

- `/api/v1/admin/status`: System status overview
- `/api/v1/admin/config`: Current configuration
- `/api/v1/admin/users`: User and subscription information
- `/api/v1/admin/models`: Available AI models
- `/api/v1/admin/usage/stats`: Platform usage statistics
- `/api/v1/admin/security/logs`: Security logs access
- `/api/v1/admin/connectors`: External API connector status

All endpoints require admin authentication via the `X-Admin-Key` header.

## Security Implementation

### Secure Configuration

The configuration system implements:

1. **Environment Detection**
   - Environment-specific security policies
   - Automatic configuration validation
   - Secure defaults for all settings

2. **Secret Management**
   - All secrets sourced from environment variables
   - Validation of required secrets in production
   - Secure generation of development secrets

### Middleware Implementation

Admin authentication is implemented through the `require_admin` decorator in `api/v1/middleware/admin_auth.py`. This middleware:

1. Verifies the admin API key is valid
2. Implements rate limiting for failed attempts
3. Uses constant-time comparison for secure key validation
4. Sets the `g.is_admin` flag for internal authorization checks

## Production Deployment Security

Before deploying to production:

1. **Required Environment Variables**
   - Set `AI_SERVICE_ENV=production`
   - Define a strong `SECRET_KEY` (min 32 chars)
   - Define a strong `ADMIN_API_KEY` (min 32 chars)
   - Configure `CORS_ORIGINS` to specific allowed domains

2. **Network Security**
   - Place API behind a reverse proxy with HTTPS
   - Configure network firewall to restrict admin endpoint access
   - Consider IP allowlisting for admin endpoints

3. **Monitoring Setup**
   - Enable security audit logging
   - Set up alerts for suspicious activity
   - Configure regular security scan reports

## Emergency Procedures

In case of a security incident:

1. Immediately revoke and rotate all API keys
2. Take detailed notes about the incident
3. Review security logs for suspicious activity
4. Implement any necessary fixes
5. Document the incident and response

## Security Roadmap

Planned security enhancements:

1. Two-factor authentication for admin access
2. IP allowlisting for admin endpoints
3. Enhanced audit logging
4. Automated security scanning
5. Secret rotation automation

## Contact for Security Issues

For urgent security questions or concerns, contact:

- Security Team: [security@techsaas.example.com](mailto:security@techsaas.example.com)
- Emergency hotline: (555) 123-4567

_Always prioritize security over convenience for admin operations._
