"""
Configuration module for the AI Service application
"""

import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BaseConfig:
    """Base configuration class for the AI Service"""
    
    # Application info
    APP_NAME = "TechSaaS AI Service"
    VERSION = "1.0.0"
    ENV = os.getenv("AI_SERVICE_ENV", "development")
    
    # Server configuration
    PORT = int(os.getenv("AI_SERVICE_PORT", 5000))
    DEBUG = bool(os.getenv("AI_SERVICE_DEBUG", "True").lower() == "true")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Auth configuration - use environment variables for sensitive data
    DISABLE_AUTH_FOR_DEV = False  # Default to requiring auth
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")  # Empty by default, must be set in env
    
    # AI model configuration
    DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "ollama/llama2")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", 2048))
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", 0.7))
    
    # LangChain configuration
    LANGCHAIN_VERBOSE = bool(os.getenv("LANGCHAIN_VERBOSE", "False").lower() == "true")
    LANGCHAIN_CACHE = bool(os.getenv("LANGCHAIN_CACHE", "True").lower() == "true")
    
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Multimodal processing configuration
    ENABLE_MULTIMODAL = bool(os.getenv("ENABLE_MULTIMODAL", "True").lower() == "true")
    MULTIMODAL_TEMP_DIR = os.getenv("MULTIMODAL_TEMP_DIR", "/tmp/techsaas-multimodal")
    
    # Storage configuration
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/tmp/techsaas-uploads")
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", 
                          "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE = os.getenv("LOG_FILE", "")  # Empty string disables file logging
    
    # API documentation settings
    API_TITLE = "TechSaaS API"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = "/api/docs"
    OPENAPI_SWAGGER_UI_PATH = "/swagger"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    OPENAPI_REDOC_PATH = "/redoc"
    OPENAPI_REDOC_URL = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
    
    # API rate limits by tier
    RATE_LIMITS = {
        "basic": {
            "per_minute": 100,
            "daily_quota": 10000
        },
        "pro": {
            "per_minute": 500,
            "daily_quota": 100000
        },
        "enterprise": {
            "per_minute": 2000,
            "daily_quota": None  # Unlimited
        }
    }
    
    # API tier model access
    TIER_MODEL_ACCESS = {
        "basic": ["ollama/llama2", "ollama/mistral"],
        "pro": ["ollama/llama2", "ollama/mistral", "ollama/codellama", "ollama/llava"],
        "enterprise": "all"  # Access to all models
    }
    
    # API tier feature access
    TIER_FEATURES = {
        "basic": ["text_analysis", "chat", "image_analysis"],
        "pro": ["text_analysis", "chat", "completion", "image_analysis", "audio_analysis"],
        "enterprise": ["text_analysis", "chat", "completion", "image_analysis", 
                      "audio_analysis", "video_analysis", "admin_tools"]
    }
    
    # Usage costs by tier and endpoint
    USAGE_COSTS = {
        "basic": {
            "analyze": 0.01,  # $ per request
            "chat": 0.005,    # $ per message
            "image": 0.02     # $ per image
        },
        "pro": {
            "analyze": 0.005,  # $ per request
            "chat": 0.003,     # $ per message
            "completion": 0.008, # $ per 1K tokens
            "image": 0.015,    # $ per image
            "audio": 0.05      # $ per minute
        },
        "enterprise": {
            "analyze": 0.002,  # $ per request
            "chat": 0.001,     # $ per message
            "completion": 0.005, # $ per 1K tokens
            "image": 0.01,     # $ per image
            "audio": 0.03,     # $ per minute
            "video": 0.10      # $ per minute
        }
    }
    
    
class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    ENV = "development"
    DEBUG = True
    TESTING = False
    
    # Safe development settings - generate a random admin key if not set
    DISABLE_AUTH_FOR_DEV = True  # Only bypass auth in development
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", secrets.token_urlsafe(32))  # Generate a secure key
    
    def __init__(self):
        super().__init__()
        # Print the admin key for local development use
        if self.DISABLE_AUTH_FOR_DEV:
            print(f"\n======================= DEVELOPMENT MODE =======================")
            print(f"AUTHENTICATION DISABLED FOR DEVELOPMENT")
            print(f"For testing admin access: ADMIN_API_KEY={self.ADMIN_API_KEY}")
            print(f"================================================================\n")


class TestingConfig(BaseConfig):
    """Testing configuration"""
    ENV = "testing"
    DEBUG = True
    TESTING = True
    DISABLE_AUTH_FOR_DEV = True  # Bypass auth for testing
    
    # Set a predictable key for testing
    ADMIN_API_KEY = "test_admin_key"  # Only for testing environment
    

class ProductionConfig(BaseConfig):
    """Production configuration"""
    ENV = "production"
    DEBUG = False
    TESTING = False
    
    # Security settings for production
    DISABLE_AUTH_FOR_DEV = False  # Never bypass auth in production
    SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in environment
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")  # Must be set in environment
    
    # Ensure required security settings are present
    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY or self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError("Production environment requires a secure SECRET_KEY to be set")
        
        if not self.ADMIN_API_KEY:
            raise ValueError("Production environment requires ADMIN_API_KEY to be set")
    
    # Production-specific settings
    LOG_LEVEL = "WARNING"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://techsaas.app").split(",")


def get_config():
    """
    Get configuration class based on environment
    
    Returns:
        object: Configuration class for the current environment
    """
    env = os.getenv("AI_SERVICE_ENV", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()
