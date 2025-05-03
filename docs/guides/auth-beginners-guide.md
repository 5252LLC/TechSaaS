# JWT Authentication for Beginners

This guide explains how to use TechSaaS's authentication system in simple terms, with complete examples.

## What is JWT Authentication?

JWT (JSON Web Token) is like a digital ID card. When you log in to TechSaaS:

1. You provide your email and password
2. The server checks if they're correct
3. If correct, it gives you a special token (your digital ID card)
4. You show this token on all future requests to prove who you are

![JWT Authentication Flow](../assets/images/jwt-flow-diagram.png)

## Getting Started: Your First Login

### Step 1: Create an Account

Before you can log in, you need an account. Here's how to register:

```python
import requests

# Replace with the actual API URL
api_url = "https://api.techsaas.tech/v1"

# Register a new account
response = requests.post(
    f"{api_url}/auth/register",
    json={
        "email": "your.email@example.com",
        "password": "your_secure_password",
        "name": "Your Name"
    }
)

# Check if registration was successful
if response.status_code == 201:
    print("Registration successful!")
    print(response.json())
else:
    print("Registration failed:")
    print(response.json())
```

### Step 2: Log In to Get Your Token

Once you have an account, you can log in to get your token:

```python
# Log in to get a token
response = requests.post(
    f"{api_url}/auth/login",
    json={
        "email": "your.email@example.com",
        "password": "your_secure_password"
    }
)

# Check if login was successful
if response.status_code == 200:
    print("Login successful!")
    # Save the token for later use
    token = response.json()["data"]["token"]
    print(f"Your token: {token}")
else:
    print("Login failed:")
    print(response.json())
```

### Step 3: Use Your Token to Access Protected Resources

Now that you have a token, you can use it to access protected resources:

```python
# Set up the headers with your token
headers = {
    "Authorization": f"Bearer {token}"
}

# Make an authenticated request to get your user profile
response = requests.get(
    f"{api_url}/user/profile",
    headers=headers
)

# Check if the request was successful
if response.status_code == 200:
    print("Profile retrieved successfully!")
    profile = response.json()["data"]
    print(f"Welcome back, {profile['name']}!")
else:
    print("Failed to retrieve profile:")
    print(response.json())
```

## Common Questions

### How long is my token valid?

Your token is valid for 30 minutes. After that, you'll need to log in again or use a refresh token.

### What if my token expires?

If your token expires, you'll get an error message like this:

```json
{
  "status": "error",
  "message": "Authentication required",
  "error": {
    "type": "token_expired",
    "details": "Expired JWT token"
  }
}
```

When this happens, simply log in again to get a new token.

### How do I log out?

To log out, you can call the logout endpoint:

```python
response = requests.post(
    f"{api_url}/auth/logout",
    headers=headers
)

if response.status_code == 200:
    print("Logged out successfully!")
else:
    print("Logout failed:")
    print(response.json())
```

## Security Tips for Beginners

1. **Never share your token** with anyone
2. **Always use HTTPS** for API requests
3. **Don't store tokens in code** - use environment variables instead
4. **Log out when you're done** using the API

## Complete Example: A Simple Login System

Here's a complete example of a simple login system:

```python
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if available)
load_dotenv()

class TechSaaSClient:
    def __init__(self, api_url=None):
        self.api_url = api_url or "https://api.techsaas.tech/v1"
        self.token = None
    
    def register(self, email, password, name):
        """Register a new user"""
        response = requests.post(
            f"{self.api_url}/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name
            }
        )
        return response.json()
    
    def login(self, email, password):
        """Log in and get a token"""
        response = requests.post(
            f"{self.api_url}/auth/login",
            json={
                "email": email,
                "password": password
            }
        )
        data = response.json()
        if response.status_code == 200:
            self.token = data["data"]["token"]
        return data
    
    def get_profile(self):
        """Get the user's profile"""
        if not self.token:
            return {"error": "Not logged in"}
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.api_url}/user/profile",
            headers=headers
        )
        return response.json()
    
    def logout(self):
        """Log out and invalidate the token"""
        if not self.token:
            return {"message": "Already logged out"}
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.api_url}/auth/logout",
            headers=headers
        )
        if response.status_code == 200:
            self.token = None
        return response.json()

# Usage example
if __name__ == "__main__":
    client = TechSaaSClient()
    
    # Register (uncomment if you need to register)
    # print(client.register("user@example.com", "secure_password", "Example User"))
    
    # Login
    login_result = client.login("user@example.com", "secure_password")
    print(f"Login result: {login_result}")
    
    # Get profile
    profile = client.get_profile()
    print(f"Profile: {profile}")
    
    # Logout
    logout_result = client.logout()
    print(f"Logout result: {logout_result}")
```

## Further Learning

When you're ready to learn more advanced concepts:

1. Check out our [Complete Authentication Documentation](../api/authentication.md)
2. Try the [Intermediate Authentication Guide](./auth-intermediate-guide.md)
3. Explore our [Authentication Code Examples](https://github.com/techsaas/auth-examples)

## Need Help?

- Join our Discord community: [https://discord.gg/techsaas](https://discord.gg/techsaas)
- Email beginner support: beginners@techsaas.tech
- Check out our video tutorials: [TechSaaS YouTube Channel](https://youtube.com/techsaas)
