# Rate Limiting & Usage Tracking

This document explains the TechSaaS API rate limiting and usage tracking system, which forms the core of our API monetization strategy.

## Overview

TechSaaS implements a tiered rate limiting system that:

1. **Prevents abuse** - Protects the platform from excessive use
2. **Ensures fair access** - Allocates resources based on subscription level 
3. **Enables billing** - Tracks API usage for pay-per-use pricing
4. **Provides analytics** - Offers insights into your API consumption patterns

## Rate Limits by Subscription Tier

Each subscription tier has different rate limits:

| Tier | Requests/Minute | Requests/Hour | Requests/Day | Pricing Model |
|------|-----------------|---------------|--------------|---------------|
| Free | 20 | 100 | 1,000 | Limited access |
| Basic | 100 | 1,000 | 10,000 | Pay-per-use |
| Pro | 500 | 5,000 | 100,000 | Pay-per-use with volume discount |
| Enterprise | 2,000 | 20,000 | Unlimited | Custom pricing |

## Rate Limit Headers

Each API response includes rate limit headers to help you track your usage:

```
X-RateLimit-Limit: 100       # Your rate limit per minute
X-RateLimit-Remaining: 95    # Remaining requests in this window
X-RateLimit-Reset: 45        # Seconds until limit resets
X-DailyQuota-Limit: 10000    # Your daily request quota
X-DailyQuota-Remaining: 9940 # Remaining requests for today
X-DailyQuota-Reset: 14400    # Seconds until daily quota resets
X-Usage-ID: 82d9e881-651b-4c1b-b8a1-d7084ae91e67  # Unique ID for this request
```

## Handling Rate Limits

### Rate Limit Response

When you exceed your rate limit, you'll receive a `429 Too Many Requests` response:

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "error": {
    "detail": "Minute limit of 100 requests exceeded",
    "status": "too_many_requests",
    "limit": 100,
    "current": 101,
    "retry_after": 45,
    "upgrade_url": "https://techsaas.tech/pricing"
  }
}
```

### Best Practices for Handling Rate Limits

1. **Monitor the headers** - Check `X-RateLimit-Remaining` to anticipate limits
2. **Implement backoff** - When rate limited, wait for `retry_after` seconds
3. **Optimize requests** - Batch operations when possible
4. **Use webhooks** - For long-running operations to reduce polling

## Code Examples

### Python: Rate Limit Handling

```python
import requests
import time

def call_api_with_backoff(url, api_key, max_retries=5):
    headers = {"Authorization": f"Bearer {api_key}"}
    retries = 0
    
    while retries < max_retries:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limited - get retry time from headers
            retry_after = int(response.headers.get('retry-after', 60))
            print(f"Rate limited, waiting for {retry_after} seconds...")
            time.sleep(retry_after)
            retries += 1
        else:
            # Handle other errors
            response.raise_for_status()
    
    raise Exception("Maximum retries exceeded")
```

### JavaScript: Rate Limit Monitoring

```javascript
async function callApiWithRateLimitTracking(url, apiKey) {
  const headers = { Authorization: `Bearer ${apiKey}` }
  
  const response = await fetch(url, { headers })
  
  // Log rate limit info
  console.log(`Rate limit: ${response.headers.get('x-ratelimit-remaining')}/${response.headers.get('x-ratelimit-limit')}`)
  console.log(`Reset in ${response.headers.get('x-ratelimit-reset')} seconds`)
  
  // Check if approaching limit (less than 10% remaining)
  const remaining = parseInt(response.headers.get('x-ratelimit-remaining'), 10)
  const limit = parseInt(response.headers.get('x-ratelimit-limit'), 10)
  
  if (remaining < limit * 0.1) {
    console.warn(`Warning: Approaching rate limit! Only ${remaining} requests remaining.`)
  }
  
  return response.json()
}
```

## Usage Tracking

The TechSaaS API tracks usage metrics for billing and analytics purposes:

1. **Request counts** - Total API calls made
2. **Compute units** - Processing resources consumed
3. **Tokens** - For AI operations (prompt + completion tokens)
4. **Storage** - Data storage used

These metrics form the basis of our pay-per-use billing model.

## Viewing Your Usage

### Usage Summary Endpoint

```
GET /api/v1/usage/summary?days=30
```

Returns a summary of your API usage for the specified period.

### Billing Data Endpoint

```
GET /api/v1/usage/billing?start_date=2025-04-01&end_date=2025-04-30
```

Returns detailed billing information for the specified period.

## Administrative Endpoints

For account administrators, additional endpoints are available:

- `/api/v1/usage/admin/user/{user_id}` - Get usage for a specific user
- `/api/v1/usage/admin/billing/{user_id}` - Get billing data for a user
- `/api/v1/usage/admin/summary` - Get overall usage summary
- `/api/v1/usage/admin/report/monthly` - Get monthly usage report
- `/api/v1/usage/admin/limits` - View current rate limit configuration

## Pricing Model

TechSaaS uses a multi-component pricing model:

1. **Base fee** - Subscription tier monthly cost
2. **Request charges** - Based on the number and type of API calls
3. **Compute charges** - Based on computational resources used
4. **Token charges** - For AI operations, based on tokens processed
5. **Storage charges** - For data storage utilized

Each tier offers different rates for these components, with higher tiers providing better rates for volume usage.

## Upgrading Your Tier

If you find yourself regularly hitting rate limits, consider upgrading your subscription:

1. Visit your [account dashboard](https://techsaas.tech/dashboard)
2. Navigate to "Subscription"
3. Select "Upgrade Plan"
4. Choose the tier that fits your usage patterns

You can also contact [sales@techsaas.tech](mailto:sales@techsaas.tech) for custom enterprise plans.
