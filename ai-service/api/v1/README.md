# TechSaaS API v1

## Overview

This directory contains the TechSaaS API v1 implementation, which provides access to AI services, user management, and advanced analytics capabilities through a secure, tiered API.

## Architecture

The API is structured with the following components:

- **Routes**: API endpoints organized into feature-specific blueprints
- **Middleware**: Security, authorization, and request processing components
- **Utils**: Helper functions, configuration, and common utilities
- **Models**: Data models and schemas
- **Services**: Business logic and service integrations

## Security Implementation

The API implements a comprehensive JWT-based security system with:

- **Authentication**: JWT token-based authentication with refresh capabilities
- **Authorization**: Role-based and tier-based access control
- **Middleware**: Security components that protect API endpoints

Please see the [security documentation](/docs/security/AUTH_SYSTEM.md) for details.

## API Features

- **AI Models**: Access to text, image, audio, and video analysis capabilities
- **User Management**: Account creation, authentication, and profile management
- **Subscription Tiers**: Feature access based on subscription level
- **Analytics**: Usage tracking and reporting
- **Administration**: User and resource management

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Set required environment variables (see Configuration section)
3. Run the development server: `FLASK_APP=app.py FLASK_DEBUG=1 flask run`

## Configuration

The API supports configuration through environment variables:

- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `JWT_ALGORITHM`: Algorithm used for token signing (default: HS256)
- `DATABASE_URL`: Database connection string
- `API_BASE_URL`: Base URL for API endpoints
- `CORS_ORIGINS`: Allowed origins for CORS

## Documentation

- [API Documentation](/docs/api/README.md): Comprehensive API documentation
- [Security Guide](/docs/security/AUTH_SYSTEM.md): Authentication and authorization details
- [Developer Guide](/docs/developers/README.md): Guide for API developers
