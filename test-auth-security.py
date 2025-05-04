#!/usr/bin/env python3
"""
Authentication Security Test Script

This script tests the security enhancements made to the TechSaaS authentication system.
It validates JWT token verification, role-based access control, and prevention of
privilege escalation attacks.

Run this script while the server is running with test routes enabled:
./run-security-test-server.sh
"""

import requests
import json
import sys
import time
from api.v1.utils.token_generator import generate_test_token

BASE_URL = 'http://localhost:5000'

# Test tokens with different roles and tiers
USER_TOKEN = generate_test_token(
    user_id="user-123",
    email="user@example.com",
    role="user",
    tier="basic"
)

PREMIUM_TOKEN = generate_test_token(
    user_id="premium-456",
    email="premium@example.com",
    role="user",
    tier="premium"
)

ADMIN_TOKEN = generate_test_token(
    user_id="admin-789",
    email="admin@example.com",
    role="admin",
    tier="enterprise"
)

# Create a tampered token with escalated privileges
def create_tampered_token(original_token, modifications):
    """Create a tampered token by modifying claims without proper signature"""
    # This is for testing only - shows how attackers might attempt to tamper
    import jwt
    from datetime import datetime, timedelta
    
    # Decode without verification to access the payload
    try:
        # This would fail with proper verification, but we're simulating tampering
        decoded = jwt.decode(original_token, options={"verify_signature": False})
        
        # Apply modifications
        for key, value in modifications.items():
            decoded[key] = value
            
        # Re-encode with a fake secret
        tampered = jwt.encode(decoded, "fake-secret-for-tampering", algorithm="HS256")
        return tampered
        
    except Exception as e:
        print(f"Error creating tampered token: {e}")
        return None

def run_tests():
    """Run a series of security tests"""
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Helper function to record test results
    def record_test(name, status, details=None):
        success = status.lower() == "pass"
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1
            
        results["tests"].append({
            "name": name,
            "status": status,
            "details": details or ""
        })
        
        # Print immediate result
        status_color = "\033[92m" if success else "\033[91m"  # Green or Red
        print(f"{status_color}{status}\033[0m: {name}")
        if details and not success:
            print(f"  → {details}")
    
    # Test 1: Public endpoint access
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status")
        if response.status_code == 200:
            record_test("Public endpoint access", "PASS")
        else:
            record_test("Public endpoint access", "FAIL", 
                       f"Expected 200 but got {response.status_code}")
    except Exception as e:
        record_test("Public endpoint access", "FAIL", str(e))
    
    # Test 2: Protected route without authentication
    try:
        response = requests.get(f"{BASE_URL}/api/v1/protected/user-profile")
        if response.status_code in [401, 403]:
            record_test("Protected route authentication", "PASS")
        else:
            record_test("Protected route authentication", "FAIL", 
                       f"Expected 401/403 but got {response.status_code}")
    except Exception as e:
        record_test("Protected route authentication", "FAIL", str(e))
    
    # Test 3: Protected route with valid authentication
    try:
        headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/protected/user-profile", headers=headers)
        if response.status_code == 200:
            record_test("Valid token authentication", "PASS")
        else:
            record_test("Valid token authentication", "FAIL", 
                       f"Expected 200 but got {response.status_code}")
    except Exception as e:
        record_test("Valid token authentication", "FAIL", str(e))
    
    # Test 4: Tampered token rejection
    try:
        tampered_token = create_tampered_token(USER_TOKEN, {"role": "admin"})
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/dashboard", headers=headers)
        if response.status_code in [401, 403]:
            record_test("Tampered token rejection", "PASS")
        else:
            record_test("Tampered token rejection", "FAIL", 
                       f"Expected 401/403 but got {response.status_code}")
    except Exception as e:
        record_test("Tampered token rejection", "FAIL", str(e))
    
    # Test 5: Role-based access control
    try:
        # User token shouldn't be able to access admin routes
        headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/dashboard", headers=headers)
        if response.status_code in [401, 403]:
            record_test("Role-based access control", "PASS")
        else:
            record_test("Role-based access control", "FAIL", 
                       f"Expected 401/403 but got {response.status_code}")
    except Exception as e:
        record_test("Role-based access control", "FAIL", str(e))
    
    # Test 6: Tier-based access control
    try:
        # Basic tier shouldn't be able to access premium features
        headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/premium/features", headers=headers)
        if response.status_code in [401, 403]:
            record_test("Tier-based access control", "PASS")
        else:
            record_test("Tier-based access control", "FAIL", 
                       f"Expected 401/403 but got {response.status_code}")
    except Exception as e:
        record_test("Tier-based access control", "FAIL", str(e))
    
    # Test 7: Premium token access to premium features
    try:
        headers = {"Authorization": f"Bearer {PREMIUM_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/premium/features", headers=headers)
        if response.status_code == 200:
            record_test("Premium tier access", "PASS")
        else:
            record_test("Premium tier access", "FAIL", 
                       f"Expected 200 but got {response.status_code}")
    except Exception as e:
        record_test("Premium tier access", "FAIL", str(e))
    
    # Test 8: Admin token access to admin dashboard
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/admin/dashboard", headers=headers)
        if response.status_code == 200:
            record_test("Admin role access", "PASS")
        else:
            record_test("Admin role access", "FAIL", 
                       f"Expected 200 but got {response.status_code}")
    except Exception as e:
        record_test("Admin role access", "FAIL", str(e))
    
    # Print summary
    print("\n" + "="*50)
    print(f"SECURITY TEST SUMMARY: {results['passed']} passed, {results['failed']} failed")
    print("="*50)
    
    return results

if __name__ == "__main__":
    print("TechSaaS Authentication Security Test")
    print("Make sure the server is running with test routes enabled:")
    print("./run-security-test-server.sh")
    print("\nRunning tests in 3 seconds...\n")
    time.sleep(3)
    
    run_tests()
