# Understanding API Billing for Beginners

This guide explains how billing works on the TechSaaS platform in simple terms. It's perfect for developers who are new to working with paid APIs.

## How API Billing Works

When you use the TechSaaS API, you're charged based on how much you use it. Think of it like your electricity bill - you pay for what you use.

![Billing Concept](../assets/images/billing-concept.png)

## What You're Charged For

We measure your API usage in several ways:

1. **API Requests** - Each time you call our API
2. **Compute Units** - How much processing power your requests use
3. **Tokens** - For AI operations, like generating text or analyzing data
4. **Storage** - How much data you store on our platform

## Subscription Tiers

We offer different subscription tiers to fit your needs:

| Tier | Monthly Fee | Benefits |
|------|-------------|----------|
| Free | $0 | 20 requests/minute, basic features, community support |
| Basic | $9.99 | 100 requests/minute, all features, email support |
| Pro | $49.99 | 500 requests/minute, advanced models, priority support |
| Enterprise | $199.99 | 2,000 requests/minute, unlimited daily usage, dedicated support |

## Understanding Your Invoice

Your invoice breaks down your usage and charges. Here's what each part means:

![Invoice Diagram](../assets/images/invoice-diagram.png)

1. **Subscription Fee** - Your monthly base fee for your tier
2. **API Requests** - How many API calls you made
3. **Compute Units** - How much processing power you used
4. **Tokens** - How many tokens your AI operations used
5. **Storage** - How much data you stored

## Example: How Costs Add Up

Let's say you're on the Basic plan ($9.99/month) and in one month you use:

- 5,000 API requests × $0.001 = $5.00
- 200 compute units × $0.01 = $2.00
- 50,000 tokens × $0.00001 = $0.50
- 100 MB storage × $0.00000001 per byte = $1.05

Your total bill would be:
$9.99 (subscription) + $5.00 + $2.00 + $0.50 + $1.05 = $18.54

## Simple Code Example: Checking Your Current Invoice

Here's a beginner-friendly Python example for checking your current bill:

```python
import requests

# Your API key from your TechSaaS account
api_key = "your_api_key_here"

# The URL to get your current invoice
url = "https://api.techsaas.tech/v1/billing/invoice"

# Add your API key to the headers
headers = {
    "Authorization": f"Bearer {api_key}"
}

# Make the API request
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Get the invoice data
    invoice = response.json()["data"]
    
    # Print the important parts of the invoice
    print(f"Billing period: {invoice['billing_period']['start_date']} to {invoice['billing_period']['end_date']}")
    print(f"Subscription: ${invoice['line_items'][0]['amount']}")
    print(f"API Requests: ${invoice['line_items'][1]['amount']}")
    print(f"Compute Units: ${invoice['line_items'][2]['amount']}")
    print(f"Tokens: ${invoice['line_items'][3]['amount']}")
    print(f"Storage: ${invoice['line_items'][4]['amount']}")
    print(f"Total: ${invoice['total']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

## Common Questions

### How often will I be billed?

You'll be billed at the end of each calendar month for your subscription and any usage during that month.

### Can I set a spending limit?

Yes! You can set a monthly spending limit in your account dashboard. Once you reach this limit, you'll be notified and can choose to increase it or pause your usage.

### What happens if I go over my rate limit?

If you exceed your rate limit, your requests will be rejected with a 429 error until the limit resets. This doesn't cost you anything extra, but it might affect your application's performance.

### How can I estimate my costs?

You can use the `/usage/summary` endpoint to see your current usage, and the `/billing/invoice` endpoint to see what your current charges look like.

### What's the difference between requests and compute units?

- **Requests** = Each time you call our API
- **Compute Units** = A measure of processing power (some operations use more than others)

## Tips for Managing Your Bill

1. **Start with the Free tier** to test your application
2. **Monitor your usage** regularly using our Dashboard or the API
3. **Choose the right tier** for your needs
4. **Optimize your requests** to reduce unnecessary API calls
5. **Use caching** for frequently accessed data

## Need More Help?

- Check out the [complete billing documentation](../api/billing-api.md)
- Join our [community forum](https://community.techsaas.tech)
- Email [support@techsaas.tech](mailto:support@techsaas.tech)
- Watch our [video tutorial series](https://youtube.com/techsaas)
