# System Architecture

## Overview

The Prediction Markets Aggregator is a data pipeline that collects real-time prediction market data from multiple sources and stores it in a centralized database for analysis.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES (APIs)                         │
├─────────────────────────────────────────────────────────────────┤
│  Polymarket  │  Kalshi  │  Opinion  │  F&G Index  │  CoinGecko │
│  (Public)    │  (Auth)  │  (API Key)│   (Public)  │  (Public)  │
└──────┬───────┴────┬─────┴─────┬─────┴──────┬──────┴──────┬─────┘
       │            │           │            │             │
       │            │           │            │             │
       └────────────┴───────────┴────────────┴─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGGREGATOR SCRIPT (Python)                   │
├─────────────────────────────────────────────────────────────────┤
│  • Reads config.yaml for keywords                               │
│  • Makes HTTP requests to each API                              │
│  • Parses JSON responses                                        │
│  • Matches markets to categories via keywords                   │
│  • Filters by volume thresholds                                 │
│  • Assigns topic tags for cross-platform comparison            │
│  • Adds UTC timestamps                                          │
│  • Handles errors gracefully                                    │
│  • Logs all operations                                          │
│  • Sends email alerts on failures                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SUPABASE (PostgreSQL)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  prediction_markets_raw                                  │  │
│  │  • source, market_id, question                           │  │
│  │  • category, topic_tag                                   │  │
│  │  • probability, volume_usd, timestamp                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  price_data                                              │  │
│  │  • asset (BTC/ETH), price_usd, timestamp                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  sentiment_data                                          │  │
│  │  • fear_greed_value, fear_greed_label, timestamp         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ANALYTICS & QUERIES                         │
├─────────────────────────────────────────────────────────────────┤
│  • Cross-platform market comparison                             │
│  • Probability trend analysis                                   │
│  • Volume tracking by category                                  │
│  • Arbitrage opportunity detection                              │
│  • Correlation with crypto prices                               │
│  • Historical data analysis                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. Configuration Layer

```
config.yaml
├── categories
│   ├── macro (keywords, min_volume_usd)
│   ├── crypto (keywords, min_volume_usd)
│   ├── geopolitics (keywords, min_volume_usd)
│   ├── politics (keywords, min_volume_usd)
│   └── companies (keywords, min_volume_usd)
├── apis
│   ├── polymarket (base_url, enabled)
│   ├── kalshi (base_url, enabled)
│   ├── opinion (base_url, enabled)
│   ├── fear_greed (base_url, enabled)
│   └── coingecko (base_url, enabled)
├── database (batch_size)
├── monitoring (email_alerts)
└── schedule (interval_minutes)
```

**Key Features**:
- Human-editable (no code changes)
- YAML format for clarity
- Supports enable/disable per API
- Flexible keyword matching

### 2. Data Collection Layer

```python
PredictionMarketsAggregator
├── __init__()
│   ├── Load configuration
│   ├── Initialize Supabase client
│   └── Create HTTP session
│
├── fetch_polymarket_markets()
│   ├── GET /markets
│   ├── Parse JSON response
│   ├── Match keywords → category + topic_tag
│   ├── Filter by volume threshold
│   └── Return list of markets
│
├── fetch_kalshi_markets()
│   ├── Login with credentials
│   ├── GET /markets (with auth header)
│   ├── Match keywords → category + topic_tag
│   ├── Filter by volume threshold
│   └── Return list of markets
│
├── fetch_opinion_markets()
│   ├── GET /markets (with API key)
│   ├── Match keywords → category + topic_tag
│   ├── Filter by volume threshold
│   └── Return list of markets
│
├── fetch_fear_greed_index()
│   ├── GET /fng/
│   └── Return sentiment data
│
├── fetch_crypto_prices()
│   ├── GET /simple/price?ids=bitcoin,ethereum
│   └── Return BTC/ETH prices
│
└── collect_all_data()
    ├── Try fetch from each source (graceful failures)
    ├── Combine all markets
    ├── Save to database
    └── Log results
```

**Error Handling Strategy**:
```
For each API:
  try:
    fetch_data()
    process_data()
  except APIError:
    log_error()
    send_alert() if persistent
    continue with other APIs
```

### 3. Keyword Matching Algorithm

```
For each market question:
  1. Convert question to lowercase
  2. For each category:
     3. For each keyword in category:
        4. If keyword appears in question:
           5. Assign category
           6. Use keyword as topic_tag (normalized)
           7. Check volume >= min_volume_usd
           8. If passes, include market
           9. Break (first match wins)
```

**Topic Tag Normalization**:
- Lowercase: "Bitcoin" → "bitcoin"
- Replace spaces: "Bank of England" → "bank_of_england"
- Replace special chars: "S&P 500" → "s_and_p_500"

**Example Matches**:
- "Will Bitcoin reach $100K?" → crypto / btc
- "Fed rate cut in 2026?" → macro / fed
- "Israel-Iran conflict escalate?" → geopolitics / iran

### 4. Database Schema

```sql
prediction_markets_raw
├── id (UUID, PK, auto)
├── source (text, CHECK in polymarket|kalshi|opinion)
├── market_id (text, platform-specific ID)
├── question (text, full question)
├── category (text, CHECK in macro|crypto|geopolitics|politics|companies)
├── topic_tag (text, normalized keyword)
├── probability (float, CHECK 0-1)
├── volume_usd (float, CHECK >= 0)
├── timestamp (timestamptz, UTC)
└── created_at (timestamptz, auto)

Indexes:
├── idx_markets_source (source)
├── idx_markets_category (category)
├── idx_markets_topic_tag (topic_tag)
├── idx_markets_timestamp (timestamp DESC)
├── idx_markets_category_timestamp (category, timestamp DESC)
└── idx_markets_topic_timestamp (topic_tag, timestamp DESC)
```

**Design Principles**:
- Append-only (no updates/deletes)
- UTC timestamps mandatory
- Indexed for fast queries
- Constraints ensure data quality

### 5. Scheduling & Execution

```
Main Process:
├── Load configuration
├── Initialize database connection
├── Run immediate collection
└── Schedule recurring execution
    ├── Every 15 minutes
    ├── schedule.run_pending()
    └── sleep(30)  # Check every 30 sec

Collection Cycle:
├── Start time logging
├── Fetch from all APIs (parallel-ish)
├── Combine results
├── Batch insert to database
├── Log completion time
└── Log total markets collected
```

**Timing**:
- Collection interval: 15 minutes (configurable)
- API timeout: 30 seconds each
- Total cycle time: ~30-60 seconds
- Database batch size: 100 records

### 6. Monitoring & Alerting

```
Monitoring Points:
├── API Success/Failure
│   └── Log each API call result
├── Database Operations
│   └── Log inserts, errors
├── Collection Metrics
│   └── Markets collected, time taken
└── System Health
    └── Memory, errors, uptime

Alert Triggers:
├── API fails 3+ times in row
├── Database save fails
├── No data collected for 1 hour
└── Scheduler crashes

Alert Delivery:
└── Email via SMTP
    ├── Subject: [Andurin Alert] {issue}
    ├── Body: Error details, timestamp
    └── Recipient: ALERT_EMAIL_TO
```

### 7. Deployment Architecture

```
Development:
├── Local machine
├── Virtual environment
├── Manual execution
└── Log file monitoring

Production (Railway/Render):
├── Git repository
│   ├── Code push triggers deploy
│   └── Environment variables in dashboard
├── Docker container
│   ├── Python 3.11 base image
│   ├── Install dependencies
│   └── Run aggregator.py
├── Background worker
│   ├── Runs 24/7
│   ├── Auto-restart on failure
│   └── Logs to dashboard
└── Free tier sufficient
    ├── Railway: 500 hours/month
    └── Render: Unlimited (sleeps after 15 min)
```

## Data Flow Example

### Example: Collecting Bitcoin Markets

```
1. Scheduler triggers collection (15:00:00 UTC)

2. Polymarket API Call:
   GET https://clob.polymarket.com/markets
   ├── Returns 500 active markets
   └── Filter: contains "Bitcoin" or "BTC"
       ├── Found 15 markets
       └── Filter: volume >= $500,000
           └── Keep 8 markets

3. Kalshi API Call:
   POST /login → Get token
   GET /markets (with token)
   ├── Returns 200 active markets
   └── Filter: contains "Bitcoin" or "BTC"
       ├── Found 6 markets
       └── Filter: volume >= $500,000
           └── Keep 4 markets

4. Opinion API Call:
   GET /markets (with API key)
   ├── Returns 150 active markets
   └── Filter: contains "Bitcoin" or "BTC"
       ├── Found 5 markets
       └── Filter: volume >= $500,000
           └── Keep 3 markets

5. Combine Results:
   Total: 15 Bitcoin markets (8 + 4 + 3)

6. Process Each Market:
   For each market:
   ├── Normalize question text
   ├── Extract probability
   ├── Assign category: "crypto"
   ├── Assign topic_tag: "btc"
   ├── Add timestamp: "2026-03-30T15:00:00Z"
   └── Prepare for insert

7. Database Insert:
   INSERT INTO prediction_markets_raw
   (source, market_id, question, category, topic_tag, 
    probability, volume_usd, timestamp)
   VALUES (...), (...), ... [batch of 15]

8. Log Results:
   "✓ Collected 15 crypto markets (topic: btc)"
   "✓ Saved to database in 0.3 seconds"

9. Fetch Crypto Prices:
   GET https://api.coingecko.com/api/v3/simple/price
   ├── BTC: $68,450.23
   └── ETH: $3,234.56
   INSERT INTO price_data ...

10. Fetch Fear & Greed:
    GET https://api.alternative.me/fng/
    ├── Value: 62
    └── Label: "Greed"
    INSERT INTO sentiment_data ...

11. Cycle Complete:
    Total time: 45 seconds
    Next run: 15:15:00 UTC
```

## Scalability Considerations

### Current Capacity
- **Markets per cycle**: 10,000+
- **Database size**: Millions of rows
- **Collection time**: 30-60 seconds
- **API rate limits**: Well within free tiers
- **Cost**: $0/month (free tiers)

### Scaling Up
```
To handle more load:
├── Horizontal scaling
│   ├── Multiple worker instances
│   ├── Load balancer
│   └── Shared database
├── Increase frequency
│   ├── 5-minute intervals
│   ├── 1-minute intervals
│   └── Adjust for API rate limits
├── Add data sources
│   ├── More prediction markets
│   ├── News sources
│   └── Social sentiment
└── Database optimization
    ├── Partition by timestamp
    ├── Archive old data
    └── Read replicas for queries
```

### Performance Optimizations
```
Current:
├── Batch inserts (100 records)
├── Database indexes
├── Connection pooling
└── Async HTTP requests (future)

Potential:
├── Redis caching
├── Message queue (RabbitMQ)
├── Parallel API calls
└── Data compression
```

## Security Architecture

### Secrets Management
```
Environment Variables:
├── SUPABASE_URL (not sensitive, but don't hardcode)
├── SUPABASE_KEY (sensitive - anon key)
├── KALSHI_PASSWORD (sensitive)
├── OPINION_API_KEY (sensitive)
└── SMTP_PASSWORD (sensitive)

Never Committed:
├── .env file
├── API keys in code
└── Passwords anywhere

Stored Securely:
├── Railway/Render environment variables
├── Encrypted at rest
└── Encrypted in transit (HTTPS)
```

### API Security
```
Best Practices:
├── Use HTTPS only
├── Rotate API keys periodically
├── Rate limit compliance
├── Timeout all requests
└── Validate all responses
```

### Database Security
```
Supabase:
├── RLS (Row Level Security) optional
├── API key authentication
├── SSL connections
├── Backup & restore available
└── Audit logs
```

## Monitoring Architecture

### Logs
```
aggregator.log:
├── Timestamp
├── Log level (INFO/WARNING/ERROR)
├── Component
└── Message

Example:
2026-03-30 15:00:00 - INFO - Polymarket: Fetched 500 markets
2026-03-30 15:00:05 - INFO - Database: Saved 15 markets
2026-03-30 15:00:10 - ERROR - Kalshi: Login failed
```

### Metrics to Track
```
Collection Metrics:
├── Markets collected per source
├── Markets after filtering
├── Collection cycle time
├── Success rate
└── API response times

Data Metrics:
├── Total rows per table
├── Growth rate
├── Data quality (NULL checks)
└── Duplicate detection

System Metrics:
├── Memory usage
├── CPU usage
├── Disk space
└── Uptime
```

## Future Architecture

### Potential Enhancements
```
Phase 2:
├── REST API for frontend
├── WebSocket real-time updates
├── User authentication
└── Rate limiting

Phase 3:
├── Machine learning predictions
├── Automated trading signals
├── Alert system for users
└── Mobile app

Phase 4:
├── Multi-region deployment
├── CDN for static content
├── Advanced analytics
└── Enterprise features
```

---

## Summary

This architecture provides:
- ✅ Scalable data collection
- ✅ Reliable error handling
- ✅ Flexible configuration
- ✅ Production-ready deployment
- ✅ Comprehensive monitoring
- ✅ Future-proof design

**Built for Andurin.ai's prediction markets intelligence platform.**
