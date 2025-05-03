"""
Token Test Endpoints
Simple endpoints to test JWT token generation and verification.
"""

from flask import Blueprint, jsonify, g, request
import logging
import jwt

from api.v1.utils.token_generator import generate_test_token, get_test_tokens
from api.v1.utils.response_formatter import ResponseFormatter
from api.v1.middleware import jwt_required
from api.v1.utils.config import JWT_SECRET_KEY, JWT_ALGORITHM

# Setup logger
logger = logging.getLogger(__name__)

# Create blueprint
token_test_bp = Blueprint('token_test', __name__, url_prefix='/api/v1/token-test')

@token_test_bp.route('/generate/<role>/<tier>', methods=['GET'])
def generate_token(role, tier):
    """Generate a test token with specified role and tier"""
    try:
        # Generate token with specified role and tier
        token = generate_test_token(
            user_id=f"test-{role}-{tier}",
            email=f"{role}.{tier}@techsaas.tech",
            role=role,
            tier=tier
        )
        
        # Return token
        return ResponseFormatter.success_response(
            message=f"Generated test token for {role} / {tier}",
            data={
                "token": token,
                "role": role,
                "tier": tier,
                "usage": f"curl -H 'Authorization: Bearer {token}' http://localhost:5552/api/v1/protected/basic"
            }
        )
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return ResponseFormatter.error_response(
            message="Failed to generate token",
            error=str(e),
            error_type="token_generation_error",
            status_code=500
        )

@token_test_bp.route('/predefined', methods=['GET'])
def get_predefined_tokens():
    """Get predefined test tokens for all roles and tiers"""
    try:
        # Get all predefined tokens
        tokens = get_test_tokens()
        
        # Format response
        token_data = {}
        for key, token in tokens.items():
            token_data[key] = {
                "token": token,
                "curl_command": f"curl -H 'Authorization: Bearer {token}' http://localhost:5552/api/v1/protected/basic"
            }
        
        # Return tokens
        return ResponseFormatter.success_response(
            message="Predefined test tokens",
            data=token_data
        )
    except Exception as e:
        logger.error(f"Error getting predefined tokens: {str(e)}")
        return ResponseFormatter.error_response(
            message="Failed to get predefined tokens",
            error=str(e),
            error_type="token_generation_error",
            status_code=500
        )

@token_test_bp.route('/verify', methods=['GET'])
@jwt_required
def verify_token():
    """Verify the provided JWT token and return user info"""
    # If we reach here, the token is valid (thanks to @jwt_required)
    return ResponseFormatter.success_response(
        message="Token verification successful",
        data={
            "user_id": g.user.get('sub'),
            "email": g.user.get('email'),
            "role": g.user.get('role'),
            "tier": g.user.get('tier')
        }
    )

@token_test_bp.route('/debug', methods=['GET'])
def debug_token():
    """Debug endpoint to manually decode and verify a token"""
    try:
        # Get token from headers
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            token = auth_header
        
        # Try to decode token without verification
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"Unverified token payload: {unverified_payload}")
        except:
            unverified_payload = "Failed to decode without verification"
        
        # Try to decode token with verification
        try:
            verified_payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            verification_status = "Token verification successful"
        except jwt.ExpiredSignatureError:
            verified_payload = "Token has expired"
            verification_status = "Expired token"
        except jwt.InvalidTokenError as e:
            verified_payload = f"Invalid token: {str(e)}"
            verification_status = "Invalid token"
        except Exception as e:
            verified_payload = f"Error: {str(e)}"
            verification_status = "Error"
        
        # Return debug info
        return ResponseFormatter.success_response(
            message="Token debug information",
            data={
                "token": token,
                "secret_key_used": JWT_SECRET_KEY[:3] + "..." if JWT_SECRET_KEY else "None",
                "algorithm_used": JWT_ALGORITHM,
                "verification_status": verification_status,
                "unverified_payload": unverified_payload,
                "verified_payload": verified_payload,
                "env_vars": {
                    "jwt_secret_key_set": JWT_SECRET_KEY != "development-secret-key-change-in-production",
                    "jwt_algorithm_set": JWT_ALGORITHM == "HS256"
                }
            }
        )
    except Exception as e:
        logger.error(f"Error debugging token: {str(e)}")
        return ResponseFormatter.error_response(
            message="Failed to debug token",
            error=str(e),
            error_type="token_debug_error",
            status_code=500
        )
