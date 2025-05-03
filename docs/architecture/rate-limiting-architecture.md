# Rate Limiting & Usage Tracking: System Architecture

This document provides a comprehensive overview of the TechSaaS rate limiting and usage tracking architecture. It covers system design, data flows, persistence strategies, and scaling considerations.

## System Overview

![Rate Limiting Architecture](../assets/images/rate-limit-architecture.png)

The TechSaaS rate limiting and usage tracking system consists of several integrated components:

1. **Request Authentication Layer**
   - JWT token verification
   - User and permission extraction
   - Tier identification

2. **Rate Limiting Service**
   - Redis-based distributed rate counter
   - Multi-window tracking (minute, hour, day)
   - Tier-based limit enforcement

3. **Usage Tracking Service**
   - Request metadata capture
   - Metric aggregation
   - Data persistence

4. **Analytics & Billing Service**
   - Usage data aggregation
   - Cost calculation
   - Report generation

## Rate Limiting Architecture

### Core Components

The rate limiting system uses a Redis-based implementation for performance and scalability:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  API Gateway    │────▶│  Auth Middleware │────▶│ Rate Limiter    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Redis Cluster  │
                                                └─────────────────┘
```

### Data Structure

Rate limiting uses specialized Redis data structures:

1. **Rate Counters**: Stored as Redis string values with automatic expiration
   - Key format: `ratelimit:{user_id}:{time_window}`
   - Value: Integer count of requests in the window

2. **Window Management**: Auto-expiry TTL mechanics for time windows
   - Minute window: 120 seconds TTL
   - Hour window: 3600 seconds TTL
   - Day window: 86400 seconds TTL

### Algorithm

The system uses a sliding window counter algorithm:

1. Current time is bucketed into discrete windows
2. Each request increments a counter for the current window
3. Windows automatically expire after their time period
4. Rate limit headers provide visibility into current limits

### Implementation Details

```
                ┌─────────────────┐
                │ Request         │
                └────────┬────────┘
                         │
                         ▼
┌───────────────────────────────────────────┐
│ 1. Extract user ID and tier from JWT      │
└───────────────────────┬───────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────┐
│ 2. Determine rate limit for tier          │
└───────────────────────┬───────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────┐
│ 3. Calculate current window key           │
│    window = floor(current_time / window_size)│
└───────────────────────┬───────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────┐
│ 4. Atomically increment counter in Redis  │
│    MULTI                                  │
│      INCR {user}:{tier}:{window}          │
│      EXPIRE {user}:{tier}:{window} {ttl}  │
│    EXEC                                   │
└───────────────────────┬───────────────────┘
                         │
                         ▼
      ┌─────────────────────────────────┐
      │ Is count > limit?               │
      └──────────┬──────────────────────┘
                 │
       ┌─────────┴────────┐
       │                  │
       ▼                  ▼
┌────────────┐    ┌─────────────────┐
│    Yes     │    │       No        │
└──────┬─────┘    └────────┬────────┘
       │                   │
       ▼                   ▼
┌────────────┐    ┌─────────────────┐
│Return 429  │    │Process Request  │
└────────────┘    └─────────────────┘
```

## Usage Tracking Architecture

### Core Components

The usage tracking system follows a multi-stage architecture:

```
                     ┌─────────────────┐
                     │   API Request   │
                     └────────┬────────┘
                              ▼
┌────────────────┐   ┌─────────────────┐   ┌───────────────┐
│Before Request  │──▶│  Route Handler  │──▶│After Request  │
└────────┬───────┘   └─────────────────┘   └───────┬───────┘
         │                                         │
         │           ┌─────────────────┐           │
         └──────────▶│Usage Collector  │◀──────────┘
                     └────────┬────────┘
                              │
                     ┌────────┴────────┐
                     │                 │
                     ▼                 ▼
              ┌─────────────┐   ┌─────────────┐
              │Redis (Real- │   │ SQL Database│
              │time tracking)│   │(Persistence)│
              └─────────────┘   └─────────────┘
                     │                 │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │Analytics & Bill │
                     │ Generation      │
                     └─────────────────┘
```

### Data Flow

1. **Request Capture**
   - Decorator pattern intercepts requests and responses
   - Extracts user ID, tier, and operation details
   - Measures duration and resource usage

2. **Metric Collection**
   - CPU time, memory usage
   - Token count for AI operations
   - Storage bytes for data operations
   - Request/response sizes

3. **Data Storage**
   - Short-term: Redis for realtime visibility and aggregation
   - Long-term: SQL database for persistence and analysis
   - Aggregation: Daily rollups for efficient reporting

### Implementation Details

The usage tracking implementation uses a dual-storage approach:

1. **Real-time Layer** (Redis)
   - Request counts by user, category, and operation
   - Sliding window aggregation (minute, hour, day)
   - Expiring data with configurable retention

2. **Persistence Layer** (PostgreSQL)
   - Individual request records with full metadata
   - Daily aggregation tables for reporting efficiency
   - Billing-focused data structures

## Data Model

### Usage Records Schema

```
UsageRecord
├── id: UUID (primary key)
├── user_id: String (foreign key)
├── timestamp: DateTime
├── category: String
├── operation: String
├── tier: String
├── endpoint: String
├── status_code: Integer
├── duration_ms: Integer
├── success: Boolean
└── metrics: Nested object
    ├── tokens: Integer
    ├── prompt_tokens: Integer  
    ├── completion_tokens: Integer
    ├── compute_units: Float
    └── storage_bytes: Integer
```

### Aggregation Schema

```
DailyUsage
├── user_id: String
├── date: Date
├── category: String
├── request_count: Integer
├── success_count: Integer
├── error_count: Integer
├── total_duration_ms: Integer
└── metrics: Nested object
    ├── tokens: Integer
    ├── compute_units: Float
    └── storage_bytes: Integer
```

### Billing Schema

```
BillingRecord
├── id: UUID
├── user_id: String
├── period_start: Date
├── period_end: Date
├── tier: String
├── base_amount: Decimal
├── usage_amount: Decimal
├── total_amount: Decimal
└── line_items: Array of
    ├── category: String
    ├── description: String
    ├── quantity: Integer
    ├── unit_price: Decimal
    └── amount: Decimal
```

## Scaling Considerations

### Horizontal Scaling

The system is designed for horizontal scaling:

1. **Redis Cluster**
   - Sharded by user ID for even distribution
   - Redis Cluster for automatic shard management
   - Read replicas for query offloading

2. **Database Scaling**
   - Partitioning by time periods for historical data
   - Read replicas for reporting workloads
   - Daily aggregation for efficient querying

### High Availability

1. **Redis Sentinel**
   - Automatic failover for Redis instances
   - Configurable quorum for split-brain prevention

2. **Database HA**
   - Primary/standby configuration
   - Automatic failover with monitoring

### Multi-Region Support

For global deployment, the system supports multi-region architecture:

1. **Regional Redis Instances**
   - Local rate limiting for low latency
   - Cross-region synchronization for global limits

2. **Data Aggregation**
   - Region-specific usage tracking
   - Global rollup for unified billing and reporting

## Security Considerations

### Data Protection

1. **Sensitive Data Handling**
   - PII excluded from usage tracking
   - Request content hashed or excluded
   - Compliance with data protection regulations

2. **Access Controls**
   - Role-based access to usage data
   - Admin privileges required for user data access
   - Audit logging for data access events

### Rate Limit Security

1. **Distributed Denial of Service Protection**
   - IP-based rate limiting as first defense
   - User-based limits as secondary protection
   - Automatic blocking for excessive violations

2. **Authentication Integration**
   - JWT-based identity verification
   - No rate limit bypass for authenticated users
   - Tier-specific limits based on verified identity

## Performance Optimization

### Latency Minimization

The system is designed for minimal impact on API response times:

1. **Asynchronous Processing**
   - Usage data written asynchronously
   - Non-blocking Redis operations
   - Background aggregation and persistence

2. **Caching Strategy**
   - Rate limit counters cached in memory
   - Tier information cached for quick lookups
   - Usage summaries cached with time-based invalidation

### Benchmarks

Performance testing shows minimal overhead:

| Component | Average Latency Impact |
|-----------|------------------------|
| Rate Limiting | 2-5ms |
| Usage Tracking | 1-3ms |
| Combined Overhead | 3-8ms |

## Configuration Parameters

The system is highly configurable through environment variables:

```
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_CLUSTER_URLS=redis://node1:6379,redis://node2:6379
REDIS_PASSWORD=******

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STRATEGY=redis
RATE_LIMIT_FALLBACK_STRATEGY=fixed

# Tier-based Limits (requests per minute)
RATE_LIMIT_FREE=20
RATE_LIMIT_BASIC=100
RATE_LIMIT_PRO=500
RATE_LIMIT_ENTERPRISE=2000

# Usage Tracking Configuration
USAGE_TRACKING_ENABLED=true
USAGE_TRACKING_PERSISTENCE=true
USAGE_TRACKING_ASYNC=true
USAGE_TRACKING_RETENTION_DAYS=90

# Database Configuration
DB_CONNECTION_STRING=postgresql://user:password@localhost/usage_db
DB_POOL_SIZE=10
DB_SSL_MODE=require
```

## Monitoring & Observability

### Key Metrics

The system exposes the following metrics for monitoring:

1. **Rate Limiting Metrics**
   - Rate limit hits per second
   - Rate limit rejections by tier
   - Redis operation latency

2. **Usage Tracking Metrics**
   - Requests per second by category
   - Storage rate (bytes/second)
   - Token consumption rate

### Alerting

Recommended alert configurations:

1. **Rate Limit Alerts**
   - Excessive rejection rates (>10% of traffic)
   - Rapid increases in rejection rate (>2x baseline)

2. **Usage Tracking Alerts**
   - Failed persistence operations
   - Unusual usage patterns (>3σ from baseline)

## Disaster Recovery

### Data Recovery

In case of component failure:

1. **Redis Failure**
   - Automatic failover to replica
   - In-memory fallback with fixed limits
   - Automatic reconnection and recovery

2. **Database Failure**
   - Buffered writes with persistent queue
   - Automatic replay on reconnection
   - Manual recovery procedures for extended outages

### Backup Strategy

1. **Redis Persistence**
   - RDB snapshots every 15 minutes
   - AOF persistence for transaction logging
   - Off-site backup storage

2. **Database Backups**
   - Daily full backups
   - Transaction log shipping
   - Point-in-time recovery capability

## Integration Points

### External System Integration

The rate limiting and usage tracking system integrates with:

1. **Authentication System**
   - JWT token verification
   - User tier determination
   - Permission checking

2. **Billing System**
   - Usage data export
   - Invoice generation triggers
   - Payment processing integration

3. **Analytics Platform**
   - Usage data streaming
   - Custom metrics publishing
   - Dashboard integration

### API Endpoints

Management API endpoints:

| Endpoint | Description |
|----------|-------------|
| GET /usage/summary | User's usage summary |
| GET /usage/billing | User's billing data |
| GET /admin/user/{id}/usage | Admin access to user usage |
| GET /admin/report/monthly | Monthly aggregated report |
| GET /admin/limits | Current rate limit configuration |

## Implementation Roadmap

### Phase 1: Core Infrastructure (Complete)

- Basic Redis-based rate limiting
- Simple usage tracking with Redis
- JWT integration for user identification

### Phase 2: Persistence & Reporting (Current)

- Database schema implementation
- Usage data persistence
- Basic reporting endpoints

### Phase 3: Advanced Features (Future)

- Multi-region support
- Advanced analytics 
- Machine learning for anomaly detection
- Predictive billing projections

## Appendix: Performance Testing Results

### Benchmark Methodology

Performance tests were conducted with the following parameters:

- 1000 concurrent users
- Sustained 5000 requests per second
- 10-minute test duration
- Distributed client locations

### Results

| Metric | Without Rate Limiting | With Rate Limiting | Difference |
|--------|------------------------|-------------------|------------|
| Avg. Response Time | 45ms | 48ms | +3ms (6.7%) |
| 95th Percentile | 78ms | 84ms | +6ms (7.7%) |
| 99th Percentile | 112ms | 119ms | +7ms (6.3%) |
| Throughput | 5023 rps | 5018 rps | -5 rps (0.1%) |

## Appendix: Request Flow Diagram

```
┌───────────┐         ┌──────────────┐        ┌────────────┐
│ API Client│         │API Gateway   │        │Auth Service│
└─────┬─────┘         └──────┬───────┘        └─────┬──────┘
      │    HTTP Request      │                      │
      │───────────────────────>                     │
      │                       │                     │
      │                       │  Validate JWT       │
      │                       │────────────────────>│
      │                       │                     │
      │                       │  User + Tier        │
      │                       │<────────────────────│
      │                       │                     │
      │                       │                     │
┌─────┴─────┐         ┌──────┴───────┐        ┌─────┴──────┐
│ API Client│         │Rate Limiter  │        │Redis Cluster│
└─────┬─────┘         └──────┬───────┘        └─────┬──────┘
      │                       │  Check Limit        │
      │                       │────────────────────>│
      │                       │                     │
      │                       │  Current Count      │
      │                       │<────────────────────│
      │                       │                     │
      │   Pass/Reject         │                     │
      │<──────────────────────│                     │
      │                       │                     │
┌─────┴─────┐         ┌──────┴───────┐        ┌─────┴──────┐
│ API Client│         │API Service   │        │Usage Tracker│
└─────┬─────┘         └──────┬───────┘        └─────┬──────┘
      │                       │                     │
      │                       │  Process Request    │
      │                       │─────────┐           │
      │                       │         │           │
      │                       │<────────┘           │
      │                       │                     │
      │                       │  Track Usage        │
      │                       │────────────────────>│
      │                       │                     │
      │   HTTP Response       │                     │
      │<──────────────────────│                     │
      │                       │                     │
```

## Appendix: Decision Log

### Key Architecture Decisions

1. **Redis for Rate Limiting**
   - Decision: Use Redis instead of in-memory counters
   - Rationale: Scalability, persistence, and distributed capabilities
   - Alternatives considered: In-memory counters, DynamoDB, Cassandra

2. **Dual Storage for Usage Data**
   - Decision: Redis for real-time + SQL for persistence
   - Rationale: Balance between performance and durability
   - Alternatives considered: Single storage solution, event streaming

3. **JWT for User Identity**
   - Decision: Extract user information from JWT tokens
   - Rationale: Consistent with authentication architecture, stateless
   - Alternatives considered: Separate API key management

4. **Decorator Pattern for Usage Tracking**
   - Decision: Use decorator pattern instead of middleware
   - Rationale: Granular control, explicit tracking points
   - Alternatives considered: Global middleware, aspect-oriented approach
