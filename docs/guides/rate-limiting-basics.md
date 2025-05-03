# Understanding API Rate Limits for Beginners

This guide explains rate limiting and usage tracking in simple terms for developers who are new to working with APIs.

## What is Rate Limiting?

Rate limiting is like a traffic light for API requests. It controls how many requests you can make in a certain time period.

![Rate Limiting Concept](../assets/images/rate-limit-concept.png)

Think of it this way:

- If you have a **Free** account, you can make 20 requests per minute (like a small road)
- If you have a **Basic** account, you can make 100 requests per minute (like a larger road)
- If you have a **Pro** account, you can make 500 requests per minute (like a highway)
- If you have an **Enterprise** account, you can make 2,000 requests per minute (like a superhighway)

## Why Do APIs Have Rate Limits?

Rate limits exist for three main reasons:

1. **Protect the service** - Prevents the API from being overwhelmed
2. **Fair sharing** - Makes sure everyone gets their fair share
3. **Business model** - Different subscription tiers get different access levels

## How to Know Your Limits

Every response from our API includes special headers that tell you about your rate limits:

```
X-RateLimit-Limit: 100       <- Your maximum requests per minute
X-RateLimit-Remaining: 95    <- How many requests you have left
X-RateLimit-Reset: 45        <- Seconds until your limit resets
```

## What Happens When You Hit a Rate Limit?

When you make too many requests too quickly, you'll get a `429 Too Many Requests` response. It looks like this:

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "error": {
    "detail": "Minute limit of 100 requests exceeded",
    "retry_after": 45
  }
}
```

The `retry_after` value tells you how many seconds to wait before trying again.

## Simple Example: Handling Rate Limits

Here's a beginner-friendly Python example for handling rate limits:

```python
import requests
import time

# Your API key from your TechSaaS account
api_key = "your_api_key_here"

# The URL you want to call
url = "https://api.techsaas.tech/v1/ai/generate-text"

# Your request data
data = {
    "prompt": "Write a short poem about coding"
}

# Add your API key to the headers
headers = {
    "Authorization": f"Bearer {api_key}"
}

# Function to make an API call with rate limit handling
def call_api_safely():
    while True:
        # Make the API request
        response = requests.post(url, json=data, headers=headers)
        
        # If successful, return the result
        if response.status_code == 200:
            return response.json()
        
        # If rate limited, wait and try again
        elif response.status_code == 429:
            # Get how long to wait from the response
            wait_seconds = int(response.headers.get("Retry-After", 60))
            
            print(f"Rate limit hit! Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            
            # Loop will try again after waiting
        
        # If there's another error, stop and show the error
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            break

# Call the API with rate limit handling
result = call_api_safely()
print(result)
```

## How to Monitor Your Usage

You can check how much of the API you've used by calling the usage summary endpoint:

```python
import requests

api_key = "your_api_key_here"
headers = {"Authorization": f"Bearer {api_key}"}

# Get your usage for the last 30 days
response = requests.get(
    "https://api.techsaas.tech/v1/usage/summary", 
    headers=headers
)

if response.status_code == 200:
    usage = response.json()
    print(f"Total API calls: {usage['data']['requests']['total']}")
    print(f"AI calls: {usage['data']['requests']['by_category'].get('ai', 0)}")
    print(f"Multimodal calls: {usage['data']['requests']['by_category'].get('multimodal', 0)}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

## Tips for Beginners

1. **Start slow** - Begin with a few requests to understand the API
2. **Watch the headers** - Check `X-RateLimit-Remaining` to see how many requests you have left
3. **Add delays** - If you're making multiple requests, add small delays between them
4. **Handle rate limits** - Always include code to handle rate limit responses
5. **Batch requests** - Combine multiple operations into a single API call when possible

## Common Questions

### How do I know what tier I'm on?

You can find your subscription tier in your [account dashboard](https://techsaas.tech/dashboard) or by checking the API response headers.

### What if I need more requests?

If you regularly hit rate limits, it might be time to upgrade your subscription. Visit your account dashboard to see upgrade options.

### How much will I be charged?

TechSaaS uses a "pay for what you use" model. You can view your current billing information at the `/usage/billing` endpoint to estimate costs.

### Do unused requests roll over?

No, rate limits reset after their time window (per minute, hour, or day). Unused requests don't accumulate.

## Need More Help?

- Check out the [complete rate limiting documentation](../api/rate-limiting.md)
- Join our [community forum](https://community.techsaas.tech)
- Email [support@techsaas.tech](mailto:support@techsaas.tech)
- Watch our [video tutorial series](https://youtube.com/techsaas)
