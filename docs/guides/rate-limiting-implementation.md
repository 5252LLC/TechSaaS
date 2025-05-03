# Rate Limiting & Usage Tracking: Implementation Guide

This guide provides practical implementation patterns for working with TechSaaS's rate limiting and usage tracking system.

## Quick Reference

```python
# Python Client Example
from techsaas import Client

# Initialize with rate limit handling
client = Client(
    api_key="your_api_key",
    auto_retry=True,          # Auto-retry on rate limit
    max_retries=5,            # Maximum retry attempts
    min_retry_delay=1,        # Minimum seconds between retries
    retry_backoff_factor=2,   # Exponential backoff multiplier
    retry_status_codes=[429]  # Status codes to retry
)

# Make API calls
response = client.ai.generate_text(prompt="Hello, world!")

# Check rate limit status
print(f"Rate limit: {client.rate_limit_remaining}/{client.rate_limit_total}")
print(f"Resets in {client.rate_limit_reset} seconds")
```

```javascript
// JavaScript Client Example
import { TechSaasClient } from '@techsaas/sdk';

// Initialize with rate limit handling
const client = new TechSaasClient({
  apiKey: 'your_api_key',
  autoRetry: true,           // Auto-retry on rate limit
  maxRetries: 5,             // Maximum retry attempts
  minRetryDelay: 1000,       // Minimum milliseconds between retries
  retryBackoffFactor: 2,     // Exponential backoff multiplier
  retryStatusCodes: [429]    // Status codes to retry
});

// Make API calls with rate limit monitoring
client.ai.generateText({ prompt: 'Hello, world!' })
  .then(response => {
    console.log(response.data);
    
    // Check rate limit status
    console.log(`Rate limit: ${client.rateLimitRemaining}/${client.rateLimitTotal}`);
    console.log(`Resets in ${client.rateLimitReset} seconds`);
  })
  .catch(error => {
    if (error.status === 429) {
      console.error('Rate limit exceeded despite auto-retry');
    } else {
      console.error('API error:', error);
    }
  });
```

## Rate Limiting Implementation Patterns

### Redis-Based Rate Limiting

TechSaaS uses Redis for distributed rate limiting. Here's how to implement a similar system:

```python
import redis
import time

class RedisRateLimiter:
    def __init__(self, redis_url='redis://localhost:6379/0'):
        self.redis = redis.from_url(redis_url)
    
    def check_rate_limit(self, key, limit, window_seconds=60):
        """Check if rate limit is exceeded for the key"""
        current_window = int(time.time() / window_seconds)
        window_key = f"ratelimit:{key}:{current_window}"
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds * 2)  # 2x window for safety
        result = pipe.execute()
        
        current_count = result[0]
        
        return {
            'exceeded': current_count > limit,
            'current': current_count,
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'reset': window_seconds - (int(time.time()) % window_seconds)
        }
```

### Scalable Usage Tracking Pattern

```python
import json
import time
import uuid
from datetime import datetime

class UsageTracker:
    def __init__(self, redis_client, persistent_storage=None):
        self.redis = redis_client
        self.storage = persistent_storage
    
    def track_request(self, user_id, category, operation=None, metrics=None):
        """Track API usage in Redis + optional persistent storage"""
        
        # Create usage record
        usage_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        usage_data = {
            'id': usage_id,
            'user_id': user_id,
            'timestamp': timestamp,
            'category': category,
            'operation': operation,
            'metrics': metrics or {}
        }
        
        # Store in Redis (short-term)
        redis_key = f"usage:{user_id}:{timestamp}"
        self.redis.setex(redis_key, 86400, json.dumps(usage_data))
        
        # Increment counters
        day_key = datetime.utcnow().strftime('%Y-%m-%d')
        counter_key = f"usage_count:{user_id}:{day_key}"
        self.redis.hincrby(counter_key, category, 1)
        
        # Track metrics
        if metrics:
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)):
                    metric_key = f"metric:{user_id}:{day_key}:{metric_name}"
                    self.redis.incrbyfloat(metric_key, float(value))
        
        # Store in persistent storage if available
        if self.storage:
            self.storage.save_usage(usage_data)
        
        return usage_id
```

## Usage Monitoring & Retry Framework

Here's a comprehensive implementation for handling rate limits, monitoring usage, and implementing retry logic:

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RateLimitRetry(Retry):
    """Custom retry strategy for rate limiting"""
    
    def __init__(self, **kwargs):
        self.retry_after_callback = kwargs.pop('retry_after_callback', None)
        super().__init__(**kwargs)
    
    def get_retry_after(self, response):
        """Get retry delay from response headers"""
        retry_after = response.headers.get('Retry-After')
        
        if retry_after:
            try:
                # Try to parse as seconds
                return int(retry_after)
            except ValueError:
                # Try to parse as HTTP date
                pass
                
        # Default to rate limit reset time
        reset = response.headers.get('X-RateLimit-Reset')
        if reset:
            try:
                return int(reset)
            except ValueError:
                pass
        
        # Fallback to default strategy
        return super().get_retry_after(response)

    def increment(self, method, url, *args, **kwargs):
        """Custom increment that calls the callback"""
        response = kwargs.get('response')
        
        retry_state = super().increment(method, url, *args, **kwargs)
        
        # Call callback with retry information
        if response and response.status_code == 429 and self.retry_after_callback:
            retry_after = self.get_retry_after(response)
            remaining = retry_state.get_backoff_time()
            
            self.retry_after_callback(
                retry_state.total,
                retry_state.status,
                response,
                retry_after or remaining
            )
        
        return retry_state


class TechSaasClient:
    """API client with advanced rate limit handling"""
    
    def __init__(self, api_key, base_url="https://api.techsaas.tech/v1",
                auto_retry=True, max_retries=3, retry_backoff_factor=1.0,
                min_retry_delay=1.0, retry_status_codes=None):
        
        self.api_key = api_key
        self.base_url = base_url
        self.auto_retry = auto_retry
        
        # Create session with custom retry strategy
        self.session = requests.Session()
        
        if auto_retry:
            retry_codes = retry_status_codes or [429, 503]
            retry_strategy = RateLimitRetry(
                total=max_retries,
                status_forcelist=retry_codes,
                backoff_factor=retry_backoff_factor,
                retry_after_callback=self._on_retry_callback
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        
        # Rate limit tracking properties
        self.rate_limit_total = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    def _on_retry_callback(self, retry_count, retry_status, response, retry_after):
        """Called when a request is being retried due to rate limiting"""
        print(f"Rate limited [Attempt {retry_count}]. Retrying in {retry_after}s...")
    
    def _update_rate_limits(self, response):
        """Update rate limit information from response headers"""
        self.rate_limit_total = int(response.headers.get('X-RateLimit-Limit', 0))
        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
    
    def request(self, method, endpoint, **kwargs):
        """Make an API request with rate limit handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add authorization header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.api_key}"
        kwargs['headers'] = headers
        
        # Make the request
        response = self.session.request(method, url, **kwargs)
        
        # Update rate limit information
        self._update_rate_limits(response)
        
        # Raise exceptions for error status codes
        response.raise_for_status()
        
        return response.json()


# Usage example
client = TechSaasClient('YOUR_API_KEY')

# Make API calls with retry handling
try:
    # This call will automatically retry on rate limit
    result = client.request('POST', '/ai/generate-text', json={
        'prompt': 'Hello, world!'
    })
    
    print(f"Response: {result}")
    print(f"Rate limit: {client.rate_limit_remaining}/{client.rate_limit_total}")
    print(f"Resets in {client.rate_limit_reset} seconds")
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded despite retry attempts")
    else:
        print(f"API error: {e}")
```

## Batch Processing Pattern

For high-volume operations, use batching to minimize rate limit impacts:

```python
from concurrent.futures import ThreadPoolExecutor
import time

class BatchProcessor:
    def __init__(self, client, batch_size=10, max_workers=5, 
                 rate_limit_buffer=0.1, delay_seconds=0.1):
        self.client = client
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.rate_limit_buffer = rate_limit_buffer
        self.delay_seconds = delay_seconds
    
    def process_items(self, items, process_func):
        """Process items in batches with rate limit awareness"""
        results = []
        
        # Split into batches
        batches = [
            items[i:i+self.batch_size] 
            for i in range(0, len(items), self.batch_size)
        ]
        
        for batch in batches:
            # Check if we're approaching rate limit
            if (self.client.rate_limit_remaining is not None and 
                self.client.rate_limit_remaining < len(batch) + 
                (self.client.rate_limit_total * self.rate_limit_buffer)):
                # Sleep until reset if we're too close to limit
                if self.client.rate_limit_reset:
                    print(f"Approaching rate limit, waiting {self.client.rate_limit_reset}s...")
                    time.sleep(self.client.rate_limit_reset)
            
            # Process batch with thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                batch_results = list(executor.map(process_func, batch))
                results.extend(batch_results)
            
            # Add small delay between batches
            time.sleep(self.delay_seconds)
        
        return results

# Usage
client = TechSaasClient('YOUR_API_KEY')
batch_processor = BatchProcessor(client)

# Define processing function
def process_item(text):
    return client.request('POST', '/ai/analyze-text', json={'text': text})

# Process a list of items with rate limit awareness
texts = ["Sample text 1", "Sample text 2", "Sample text 3", ...]
results = batch_processor.process_items(texts, process_item)
```

## Usage Tracking Implementation for JWT Authentication

If you're using JWT authentication instead of API keys, here's how to track usage:

```python
from functools import wraps
from flask import g, request, jsonify
import time
import json

def track_usage(category, operation=None):
    """
    Flask decorator for tracking API usage with JWT authentication
    
    Args:
        category (str): Usage category (ai, multimodal, etc.)
        operation (str): Specific operation
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated(*args, **kwargs):
            start_time = time.time()
            
            # Call the original function
            response = view_func(*args, **kwargs)
            
            # Track successful responses only
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                # Get user info from JWT token (in Flask g object)
                user_id = g.current_user.get('sub', 'anonymous')
                tier = g.current_user.get('tier', 'basic')
                
                # Calculate metrics
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Process response data to extract usage metrics
                metrics = {}
                
                if hasattr(response, 'get_json'):
                    try:
                        data = response.get_json()
                        if data and 'usage' in data:
                            # Extract usage metrics from response
                            usage = data.get('usage', {})
                            metrics.update(usage)
                    except:
                        pass
                
                # Track the usage
                from my_app.utils.usage_tracker import usage_tracker
                usage_id = usage_tracker.track_request(
                    user_id=user_id,
                    tier=tier,
                    category=category,
                    operation=operation,
                    duration_ms=duration_ms,
                    metrics=metrics
                )
                
                # Add usage tracking header to response
                if hasattr(response, 'headers'):
                    response.headers['X-Usage-ID'] = usage_id
            
            return response
        
        return decorated
    
    return decorator

# Usage example in Flask route
@app.route('/api/v1/ai/generate', methods=['POST'])
@jwt_required   # JWT authentication 
@track_usage('ai', 'generate')  # Usage tracking
def generate_text():
    data = request.get_json()
    result = ai_service.generate(data['prompt'])
    
    return jsonify({
        'text': result.text,
        'usage': {
            'tokens': result.usage.total_tokens,
            'prompt_tokens': result.usage.prompt_tokens,
            'completion_tokens': result.usage.completion_tokens
        }
    })
```

## Database Schema for Usage Tracking

Here's a PostgreSQL schema for persistent storage of usage data:

```sql
-- Users table (assumed to exist)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'basic'
);

-- API usage tracking
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    category VARCHAR(50) NOT NULL,
    operation VARCHAR(50),
    endpoint VARCHAR(255),
    duration_ms INTEGER NOT NULL DEFAULT 0,
    request_ip VARCHAR(50),
    status_code INTEGER,
    success BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Usage metrics
CREATE TABLE IF NOT EXISTS usage_metrics (
    usage_id UUID NOT NULL REFERENCES api_usage(id),
    metric_name VARCHAR(50) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (usage_id, metric_name)
);

-- Daily aggregated usage
CREATE TABLE IF NOT EXISTS daily_usage (
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    compute_units DOUBLE PRECISION NOT NULL DEFAULT 0,
    tokens INTEGER NOT NULL DEFAULT 0,
    storage_bytes BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date, category)
);

-- Billing records
CREATE TABLE IF NOT EXISTS billing_records (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    base_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    usage_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Billing details
CREATE TABLE IF NOT EXISTS billing_details (
    id UUID PRIMARY KEY,
    billing_id UUID NOT NULL REFERENCES billing_records(id),
    category VARCHAR(50) NOT NULL,
    item_description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 4) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_api_usage_user_id ON api_usage(user_id);
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_api_usage_category ON api_usage(category);
CREATE INDEX idx_daily_usage_user_date ON daily_usage(user_id, date);
CREATE INDEX idx_billing_records_user_period ON billing_records(user_id, billing_period_start, billing_period_end);
```

## Swagger/OpenAPI Documentation

Here's a OpenAPI 3.0 specification snippet for the rate limiting and usage endpoints:

```yaml
openapi: 3.0.0
info:
  title: TechSaaS API - Usage & Rate Limiting
  version: 1.0.0
  description: API endpoints for usage tracking and rate limiting

paths:
  /usage/summary:
    get:
      summary: Get usage summary
      description: Returns a summary of API usage for the authenticated user
      security:
        - bearerAuth: []
      parameters:
        - name: days
          in: query
          description: Number of days to include in summary
          schema:
            type: integer
            default: 30
      responses:
        '200':
          description: Usage summary
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsageSummary'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'

  /usage/billing:
    get:
      summary: Get billing data
      description: Returns billing data for the authenticated user
      security:
        - bearerAuth: []
      parameters:
        - name: start_date
          in: query
          description: Start date (YYYY-MM-DD)
          schema:
            type: string
            format: date
        - name: end_date
          in: query
          description: End date (YYYY-MM-DD)
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Billing data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BillingData'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '429':
          $ref: '#/components/responses/RateLimited'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  responses:
    RateLimited:
      description: Rate limit exceeded
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                type: string
                example: error
              message:
                type: string
                example: Rate limit exceeded
              error:
                type: object
                properties:
                  detail:
                    type: string
                    example: Minute limit of 100 requests exceeded
                  limit:
                    type: integer
                    example: 100
                  current:
                    type: integer
                    example: 101
                  retry_after:
                    type: integer
                    example: 45
      headers:
        Retry-After:
          schema:
            type: integer
          description: Seconds to wait before retrying
        X-RateLimit-Limit:
          schema:
            type: integer
          description: Rate limit ceiling
        X-RateLimit-Remaining:
          schema:
            type: integer
          description: Requests remaining in period
        X-RateLimit-Reset:
          schema:
            type: integer
          description: Seconds until rate limit resets

  schemas:
    UsageSummary:
      type: object
      properties:
        status:
          type: string
          example: success
        message:
          type: string
        data:
          type: object
          properties:
            user_id:
              type: string
              format: uuid
            period:
              type: string
              example: Last 30 days
            requests:
              type: object
              properties:
                total:
                  type: integer
                  example: 1234
                by_category:
                  type: object
                  additionalProperties:
                    type: integer
                  example:
                    ai: 567
                    multimodal: 678
            metrics:
              type: object
              additionalProperties:
                type: number
              example:
                tokens: 45678
                compute_units: 234
                storage_bytes: 1234567
            daily:
              type: array
              items:
                type: object
                properties:
                  date:
                    type: string
                    format: date
                  total:
                    type: integer
                  by_category:
                    type: object
                    additionalProperties:
                      type: integer
                  metrics:
                    type: object
                    additionalProperties:
                      type: number

    BillingData:
      type: object
      properties:
        status:
          type: string
          example: success
        message:
          type: string
        data:
          type: object
          properties:
            user_id:
              type: string
              format: uuid
            period:
              type: object
              properties:
                start:
                  type: string
                  format: date
                end:
                  type: string
                  format: date
            usage:
              type: object
              properties:
                requests:
                  type: object
                  properties:
                    total:
                      type: integer
                    by_category:
                      type: object
                compute_units:
                  type: number
                tokens:
                  type: integer
                storage_bytes:
                  type: integer
            charges:
              type: object
              properties:
                base_fee:
                  type: number
                compute_charges:
                  type: number
                token_charges:
                  type: number
                storage_charges:
                  type: number
                total:
                  type: number
```

## Multi-Region Deployment

For distributed systems, consider adopting a multi-region approach to rate limiting:

```python
import redis
import time
import hashlib

class DistributedRateLimiter:
    """Rate limiter that works across multiple regions"""
    
    def __init__(self, redis_urls):
        """
        Initialize with multiple Redis instances
        
        Args:
            redis_urls: List of Redis URLs for different regions
        """
        self.redis_clients = [redis.from_url(url) for url in redis_urls]
    
    def _get_shard(self, key):
        """Select a Redis shard based on key hash"""
        hash_int = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self.redis_clients[hash_int % len(self.redis_clients)]
    
    def check_rate_limit(self, key, limit, window_seconds=60):
        """
        Check if rate limit is exceeded across regions
        
        Uses a consistent hashing approach to shard keys
        """
        redis = self._get_shard(key)
        current_window = int(time.time() / window_seconds)
        window_key = f"ratelimit:{key}:{current_window}"
        
        pipe = redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds * 2)
        result = pipe.execute()
        
        current_count = result[0]
        
        return {
            'exceeded': current_count > limit,
            'current': current_count,
            'limit': limit,
            'remaining': max(0, limit - current_count),
            'reset': window_seconds - (int(time.time()) % window_seconds)
        }
```

This code provides a solid foundation for implementing your own rate limiting and usage tracking systems, or for advanced integrations with the TechSaaS API.
