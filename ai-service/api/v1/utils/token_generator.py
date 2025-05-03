"""
Token Generator for testing JWT authentication
This is a utility script to generate test JWT tokens for different user roles and tiers.
"""

import jwt
from datetime import datetime, timedelta
import uuid
import time

from api.v1.utils.config import JWT_SECRET_KEY, JWT_ALGORITHM

def generate_test_token(user_id=None, email=None, role="user", tier="free", expires_in_minutes=30):
    """
    Generate a test JWT token for testing authorization
    
    Args:
        user_id (str): User ID (optional, will be generated if not provided)
        email (str): User email (optional, will be generated if not provided)
        role (str): User role (default: user)
        tier (str): Subscription tier (default: free)
        expires_in_minutes (int): Token expiration time in minutes
        
    Returns:
        str: JWT token
    """
    # Generate default values if not provided
    if not user_id:
        user_id = str(uuid.uuid4())
    
    if not email:
        email = f"test.{role}@techsaas.tech"
    
    # Calculate expiration time - use integer timestamps instead of floating point
    # to avoid potential precision issues
    now = int(time.time())
    exp = now + (expires_in_minutes * 60)
    
    # Create payload with integer timestamps
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tier": tier,
        "iat": now,
        "exp": exp
    }
    
    # Generate token
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return token

# Predefined tokens for testing
def get_test_tokens():
    """
    Get predefined test tokens for different user roles and tiers
    
    Returns:
        dict: Dictionary of test tokens
    """
    return {
        "free_user": generate_test_token(
            user_id="test-free-user", 
            email="free@techsaas.tech", 
            role="user", 
            tier="free"
        ),
        "basic_user": generate_test_token(
            user_id="test-basic-user", 
            email="basic@techsaas.tech", 
            role="user", 
            tier="basic"
        ),
        "premium_user": generate_test_token(
            user_id="test-premium-user", 
            email="premium@techsaas.tech", 
            role="premium", 
            tier="premium"
        ),
        "admin": generate_test_token(
            user_id="test-admin", 
            email="admin@techsaas.tech", 
            role="admin", 
            tier="professional"
        ),
        "superadmin": generate_test_token(
            user_id="test-superadmin", 
            email="superadmin@techsaas.tech", 
            role="superadmin", 
            tier="enterprise"
        )
    }

if __name__ == "__main__":
    # When run directly, print all test tokens
    tokens = get_test_tokens()
    for name, token in tokens.items():
        print(f"{name}: {token}")
