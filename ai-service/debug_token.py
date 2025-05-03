#!/usr/bin/env python3
"""
JWT Token Debug Utility

This standalone script helps diagnose JWT token issues by decoding and verifying tokens
outside of the Flask application context.
"""

import jwt
import sys
import time
import os
from datetime import datetime, timedelta

# Set the JWT secret key to match the one in config.py
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'development-secret-key-change-in-production')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

def generate_token(user_id="test-user", email="test@example.com", role="user", tier="basic", exp_minutes=30):
    """Generate a test JWT token"""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "tier": tier,
        "iat": now,
        "exp": now + (exp_minutes * 60)
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_token(token):
    """Verify a JWT token"""
    try:
        # First decode without verification to show what's in the token
        print("\n== TOKEN PAYLOAD (UNVERIFIED) ==")
        unverified = jwt.decode(token, options={"verify_signature": False})
        for key, value in unverified.items():
            print(f"{key}: {value}")
        
        # Check for token expiration
        if 'exp' in unverified:
            exp_time = datetime.fromtimestamp(unverified['exp'])
            now = datetime.now()
            if exp_time < now:
                print(f"\nTOKEN EXPIRED: Expired at {exp_time}, current time is {now}")
            else:
                print(f"\nExpiration OK: Expires at {exp_time}, current time is {now}")
        
        # Try to verify with our secret key
        print("\n== VERIFICATION TEST ==")
        print(f"Secret Key: {JWT_SECRET_KEY[:5]}...{JWT_SECRET_KEY[-5:] if len(JWT_SECRET_KEY) > 10 else ''}")
        print(f"Algorithm: {JWT_ALGORITHM}")
        
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print("\nVERIFICATION SUCCESSFUL! Token is valid.\n")
        return True
    except jwt.ExpiredSignatureError:
        print("\nVERIFICATION FAILED: Token has expired.\n")
        return False
    except jwt.InvalidTokenError as e:
        print(f"\nVERIFICATION FAILED: Invalid token - {str(e)}\n")
        return False
    except Exception as e:
        print(f"\nVERIFICATION ERROR: {str(e)}\n")
        return False

def debug_usage():
    """Show usage instructions for this script"""
    print(f"""
JWT Token Debug Utility
=======================

Usage:
  python {sys.argv[0]} <token>     # Verify an existing token
  python {sys.argv[0]} generate    # Generate a new test token
  
Environment Variables:
  JWT_SECRET_KEY - Secret key used to sign tokens (currently: {"set" if JWT_SECRET_KEY != "development-secret-key-change-in-production" else "using default"})
  JWT_ALGORITHM - Algorithm used to sign tokens (currently: {JWT_ALGORITHM})
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        debug_usage()
    elif sys.argv[1] == "generate":
        # Parse optional arguments
        user_id = "test-user"
        email = "test@example.com"
        role = "user"
        tier = "basic"
        exp_minutes = 30
        
        # Parse additional arguments if provided
        arg_index = 2
        while arg_index < len(sys.argv):
            arg = sys.argv[arg_index]
            if arg == "--user-id" and arg_index + 1 < len(sys.argv):
                user_id = sys.argv[arg_index + 1]
                arg_index += 2
            elif arg == "--email" and arg_index + 1 < len(sys.argv):
                email = sys.argv[arg_index + 1]
                arg_index += 2
            elif arg == "--role" and arg_index + 1 < len(sys.argv):
                role = sys.argv[arg_index + 1]
                arg_index += 2
            elif arg == "--tier" and arg_index + 1 < len(sys.argv):
                tier = sys.argv[arg_index + 1]
                arg_index += 2
            elif arg == "--exp" and arg_index + 1 < len(sys.argv):
                exp_minutes = int(sys.argv[arg_index + 1])
                arg_index += 2
            else:
                arg_index += 1
        
        # Generate token
        token = generate_token(user_id, email, role, tier, exp_minutes)
        
        print("\n== GENERATED TOKEN ==")
        print(token)
        print("\n== CURL COMMAND ==")
        print(f"curl -H \"Authorization: Bearer {token}\" http://localhost:5552/api/v1/protected/basic")
        print("\n== TOKEN DETAILS ==")
        verify_token(token)
    else:
        # Assume the argument is a token to verify
        token = sys.argv[1]
        verify_token(token)
