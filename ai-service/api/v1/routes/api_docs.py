"""
API Documentation Registration
This module registers Swagger/OpenAPI documentation for API endpoints
"""

import logging

# Setup logger
logger = logging.getLogger(__name__)

def register_api_docs(api):
    """
    Register API documentation for all blueprints
    
    Args:
        api (flask_smorest.Api): Flask-Smorest API instance
    """
    # Import blueprints with API documentation
    from .ai_endpoints import ai_blueprint
    from .multimodal_endpoints import multimodal_blueprint
    from .management_endpoints import management_blueprint
    from .subscription_endpoints import subscription_blueprint
    
    # Configure blueprint documentation
    
    # AI Endpoints - add documentation metadata but don't register again
    ai_blueprint.description = "AI text processing endpoints for analysis, chat, and completion"
    ai_blueprint.doc_category = "AI Services"
    
    # Multimodal Endpoints - add documentation metadata but don't register again
    multimodal_blueprint.description = "Multimodal processing endpoints for video, image, audio, and mixed content"
    multimodal_blueprint.doc_category = "Multimodal Services"
    
    # Management Endpoints - add documentation metadata but don't register again
    management_blueprint.description = "Service management and monitoring endpoints"
    management_blueprint.doc_category = "Management"
    
    # Subscription Endpoints - add documentation metadata but don't register again
    subscription_blueprint.description = "API key and subscription management endpoints"
    subscription_blueprint.doc_category = "Subscriptions & Billing"
    
    # Add tier information and documentation tags
    
    # AI Services documentation
    api.spec.tag({
        "name": "AI Services",
        "description": """
        AI text processing and analysis services.
        
        ### API Tiers and Limits:
        
        | Tier | Rate Limit | Model Access | Max Tokens |
        |------|------------|--------------|------------|
        | Basic | 100 req/min | Base models only | 2,048 |
        | Pro | 500 req/min | All models | 8,192 |
        | Enterprise | 2000 req/min | All models + custom | 32,768 |
        """
    })
    
    # Multimodal Services documentation
    api.spec.tag({
        "name": "Multimodal Services",
        "description": """
        Multimodal content processing services for video, image, audio, and mixed content.
        
        ### API Tiers and Limits:
        
        | Tier | Rate Limit | Content Types | Max File Size |
        |------|------------|---------------|---------------|
        | Basic | 50 req/min | Image, Text | 10MB |
        | Pro | 200 req/min | Image, Text, Audio | 100MB |
        | Enterprise | 1000 req/min | Image, Text, Audio, Video | 1GB |
        """
    })
    
    # Management Services documentation
    api.spec.tag({
        "name": "Management",
        "description": """
        Service management and monitoring endpoints.
        
        ### API Tiers and Access:
        
        | Tier | Access Level | Features |
        |------|-------------|----------|
        | Basic | Limited | Basic health checks |
        | Pro | Standard | Health and status monitoring |
        | Enterprise | Full | Complete system management |
        """
    })
    
    # Subscription Services documentation
    api.spec.tag({
        "name": "Subscriptions & Billing",
        "description": """
        API key management and subscription services.
        
        ### API Key Management
        
        API keys are required for accessing the TechSaaS API and are tied to specific subscription tiers.
        Each account can have multiple API keys with different permission sets.
        
        ### Subscription Plans
        
        | Plan | Monthly Price | Rate Limit | Quota Multiplier | Custom Models |
        |------|--------------|------------|------------------|---------------|
        | Basic | $9.99 | 100 req/min | 1x | No |
        | Pro | $49.99 | 500 req/min | 10x | No |
        | Enterprise | $499.99 | 2000 req/min | Unlimited | Yes |
        
        ### Usage-Based Billing
        
        All plans include a base monthly fee plus usage-based costs for API consumption beyond the included quotas.
        """
    })
    
    logger.info("Registered API documentation for blueprints")
