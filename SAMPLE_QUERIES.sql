# Sample Queries - Prediction Markets Aggregator

This file contains useful SQL queries for analyzing the collected data. Copy these into Supabase SQL Editor.

## 📊 Basic Data Verification

### Check total records collected
```sql
SELECT 
    'prediction_markets_raw' as table_name,
    COUNT(*) as total_records
FROM prediction_markets_raw
UNION ALL
SELECT 
    'price_data' as table_name,
    COUNT(*) as total_records
FROM price_data
UNION ALL
SELECT 
    'sentiment_data' as table_name,
    COUNT(*) as total_records
FROM sentiment_data;
```

### Records per data source
```sql
SELECT 
    source,
    COUNT(*) as total_records,
    COUNT(DISTINCT market_id) as unique_markets,
    MIN(timestamp) as first_record,
    MAX(timestamp) as latest_record
FROM prediction_markets_raw
GROUP BY source
ORDER BY total_records DESC;
```

### Records per category
```sql
SELECT 
    category,
    COUNT(*) as total_records,
    AVG(volume_usd) as avg_volume,
    AVG(probability) as avg_probability,
    MIN(volume_usd) as min_volume,
    MAX(volume_usd) as max_volume
FROM prediction_markets_raw
GROUP BY category
ORDER BY total_records DESC;
```

## 🔍 Market Analysis

### Top markets by volume (last 24 hours)
```sql
SELECT 
    source,
    question,
    category,
    topic_tag,
    volume_usd,
    probability,
    timestamp
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY volume_usd DESC
LIMIT 20;
```

### Most active topics (by number of markets)
```sql
SELECT 
    topic_tag,
    category,
    COUNT(*) as market_count,
    COUNT(DISTINCT source) as platform_count,
    AVG(volume_usd) as avg_volume,
    AVG(probability) as avg_probability
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY topic_tag, category
ORDER BY market_count DESC
LIMIT 20;
```

### Cross-platform comparison (same topic on multiple platforms)
```sql
SELECT 
    topic_tag,
    source,
    question,
    probability,
    volume_usd,
    timestamp
FROM prediction_markets_raw
WHERE topic_tag IN (
    SELECT topic_tag
    FROM prediction_markets_raw
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY topic_tag
    HAVING COUNT(DISTINCT source) > 1
)
ORDER BY topic_tag, source, timestamp DESC;
```

### Probability divergence across platforms
```sql
WITH topic_stats AS (
    SELECT 
        topic_tag,
        source,
        AVG(probability) as avg_prob
    FROM prediction_markets_raw
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY topic_tag, source
)
SELECT 
    topic_tag,
    MAX(avg_prob) - MIN(avg_prob) as probability_spread,
    STRING_AGG(source || ': ' || ROUND(avg_prob::numeric, 3)::text, ', ') as platform_probabilities
FROM topic_stats
GROUP BY topic_tag
HAVING COUNT(DISTINCT source) > 1
ORDER BY probability_spread DESC
LIMIT 20;
```

## 📈 Trend Analysis

### Probability changes over time (hourly average)
```sql
SELECT 
    topic_tag,
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(probability) as avg_probability,
    AVG(volume_usd) as avg_volume,
    COUNT(*) as market_count
FROM prediction_markets_raw
WHERE topic_tag = 'btc'  -- Change to any topic_tag
    AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY topic_tag, hour
ORDER BY hour DESC;
```

### Volume trends by category
```sql
SELECT 
    category,
    DATE_TRUNC('day', timestamp) as day,
    SUM(volume_usd) as total_volume,
    COUNT(*) as market_count,
    AVG(probability) as avg_probability
FROM prediction_markets_raw
GROUP BY category, day
ORDER BY category, day DESC;
```

### Market sentiment over time
```sql
SELECT 
    category,
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(CASE WHEN probability > 0.5 THEN 1 ELSE 0 END) as bullish_ratio,
    COUNT(*) as total_markets
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY category, hour
ORDER BY hour DESC;
```

## 💰 Crypto Price Correlation

### BTC/ETH prices with market sentiment
```sql
WITH crypto_prices AS (
    SELECT 
        timestamp,
        MAX(CASE WHEN asset = 'BTC' THEN price_usd END) as btc_price,
        MAX(CASE WHEN asset = 'ETH' THEN price_usd END) as eth_price
    FROM price_data
    GROUP BY timestamp
),
crypto_markets AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        AVG(probability) as avg_btc_prob,
        AVG(volume_usd) as avg_btc_volume
    FROM prediction_markets_raw
    WHERE topic_tag = 'btc'
    GROUP BY hour
)
SELECT 
    cp.timestamp,
    cp.btc_price,
    cp.eth_price,
    cm.avg_btc_prob,
    cm.avg_btc_volume
FROM crypto_prices cp
LEFT JOIN crypto_markets cm ON DATE_TRUNC('hour', cp.timestamp) = cm.hour
WHERE cp.timestamp > NOW() - INTERVAL '7 days'
ORDER BY cp.timestamp DESC;
```

### Price movements vs Fear & Greed Index
```sql
WITH price_changes AS (
    SELECT 
        asset,
        timestamp,
        price_usd,
        LAG(price_usd) OVER (PARTITION BY asset ORDER BY timestamp) as prev_price,
        (price_usd - LAG(price_usd) OVER (PARTITION BY asset ORDER BY timestamp)) 
            / LAG(price_usd) OVER (PARTITION BY asset ORDER BY timestamp) * 100 as price_change_pct
    FROM price_data
)
SELECT 
    pc.timestamp,
    pc.asset,
    pc.price_usd,
    pc.price_change_pct,
    sd.fear_greed_value,
    sd.fear_greed_label
FROM price_changes pc
LEFT JOIN sentiment_data sd ON DATE_TRUNC('day', pc.timestamp) = DATE_TRUNC('day', sd.timestamp)
WHERE pc.timestamp > NOW() - INTERVAL '30 days'
ORDER BY pc.timestamp DESC;
```

## 🎯 High-Value Markets

### Markets with highest volume by category
```sql
SELECT DISTINCT ON (category)
    category,
    source,
    question,
    volume_usd,
    probability,
    timestamp
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY category, volume_usd DESC;
```

### Markets with extreme probabilities (>90% or <10%)
```sql
SELECT 
    source,
    question,
    category,
    topic_tag,
    probability,
    volume_usd,
    timestamp
FROM prediction_markets_raw
WHERE (probability > 0.90 OR probability < 0.10)
    AND volume_usd > 50000
    AND timestamp > NOW() - INTERVAL '7 days'
ORDER BY 
    CASE 
        WHEN probability > 0.90 THEN probability 
        ELSE -probability 
    END DESC;
```

### Rapidly changing probabilities
```sql
WITH prob_changes AS (
    SELECT 
        market_id,
        source,
        question,
        topic_tag,
        probability,
        timestamp,
        LAG(probability) OVER (PARTITION BY market_id, source ORDER BY timestamp) as prev_prob,
        ABS(probability - LAG(probability) OVER (PARTITION BY market_id, source ORDER BY timestamp)) as prob_change
    FROM prediction_markets_raw
    WHERE timestamp > NOW() - INTERVAL '24 hours'
)
SELECT 
    source,
    question,
    topic_tag,
    prev_prob as old_probability,
    probability as new_probability,
    prob_change,
    timestamp
FROM prob_changes
WHERE prob_change > 0.1  -- 10% change
ORDER BY prob_change DESC
LIMIT 20;
```

## 📊 Data Quality Checks

### Check for gaps in data collection
```sql
WITH time_series AS (
    SELECT 
        generate_series(
            (SELECT MIN(timestamp) FROM prediction_markets_raw),
            (SELECT MAX(timestamp) FROM prediction_markets_raw),
            '15 minutes'::interval
        ) as expected_timestamp
)
SELECT 
    ts.expected_timestamp,
    COUNT(pm.timestamp) as records_collected
FROM time_series ts
LEFT JOIN prediction_markets_raw pm 
    ON pm.timestamp BETWEEN ts.expected_timestamp AND ts.expected_timestamp + INTERVAL '15 minutes'
GROUP BY ts.expected_timestamp
HAVING COUNT(pm.timestamp) = 0
ORDER BY ts.expected_timestamp DESC;
```

### Collection success rate
```sql
WITH collection_windows AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        COUNT(DISTINCT DATE_TRUNC('minute', timestamp)) as collection_count
    FROM prediction_markets_raw
    GROUP BY hour
)
SELECT 
    hour,
    collection_count,
    CASE 
        WHEN collection_count >= 3 THEN 'Good'
        WHEN collection_count >= 2 THEN 'Partial'
        ELSE 'Poor'
    END as collection_status
FROM collection_windows
ORDER BY hour DESC;
```

### Duplicate detection
```sql
SELECT 
    source,
    market_id,
    timestamp,
    COUNT(*) as duplicate_count
FROM prediction_markets_raw
GROUP BY source, market_id, timestamp
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

## 🔥 Hot Topics (Trending)

### Topics with highest volume growth (last 24h vs previous 24h)
```sql
WITH current_24h AS (
    SELECT 
        topic_tag,
        SUM(volume_usd) as current_volume
    FROM prediction_markets_raw
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY topic_tag
),
previous_24h AS (
    SELECT 
        topic_tag,
        SUM(volume_usd) as previous_volume
    FROM prediction_markets_raw
    WHERE timestamp BETWEEN NOW() - INTERVAL '48 hours' AND NOW() - INTERVAL '24 hours'
    GROUP BY topic_tag
)
SELECT 
    c.topic_tag,
    c.current_volume,
    COALESCE(p.previous_volume, 0) as previous_volume,
    c.current_volume - COALESCE(p.previous_volume, 0) as volume_change,
    CASE 
        WHEN COALESCE(p.previous_volume, 0) > 0 
        THEN ((c.current_volume - p.previous_volume) / p.previous_volume * 100)
        ELSE NULL 
    END as volume_change_pct
FROM current_24h c
LEFT JOIN previous_24h p ON c.topic_tag = p.topic_tag
WHERE c.current_volume > 100000  -- Only topics with >$100k volume
ORDER BY volume_change DESC
LIMIT 20;
```

### New markets (first time seeing this market_id)
```sql
WITH first_seen AS (
    SELECT 
        source,
        market_id,
        MIN(timestamp) as first_timestamp
    FROM prediction_markets_raw
    GROUP BY source, market_id
)
SELECT 
    pm.source,
    pm.question,
    pm.category,
    pm.topic_tag,
    pm.volume_usd,
    pm.probability,
    fs.first_timestamp
FROM prediction_markets_raw pm
JOIN first_seen fs ON pm.source = fs.source AND pm.market_id = fs.market_id
WHERE fs.first_timestamp > NOW() - INTERVAL '24 hours'
ORDER BY fs.first_timestamp DESC;
```

## 📉 Export Queries

### Export for CSV (last 7 days of all markets)
```sql
SELECT 
    source,
    market_id,
    question,
    category,
    topic_tag,
    probability,
    volume_usd,
    timestamp
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;
```

### Export aggregated hourly data
```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    source,
    category,
    topic_tag,
    AVG(probability) as avg_probability,
    AVG(volume_usd) as avg_volume,
    COUNT(*) as market_count
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY hour, source, category, topic_tag
ORDER BY hour DESC, category, topic_tag;
```

---

## 💡 Tips for Using These Queries

1. **Replace topic_tag**: Change 'btc' to any topic like 'fed', 'iran', 'tesla'
2. **Adjust time ranges**: Modify INTERVAL values (24 hours, 7 days, 30 days)
3. **Add filters**: Add WHERE clauses for specific sources or categories
4. **Export results**: Use Supabase's export feature to download as CSV
5. **Create views**: Save frequently used queries as views in Supabase

## 🎯 Queries for Your Demo

When showing the system to the employer, use these:

1. **Cross-platform comparison** - Shows the same topic on multiple platforms
2. **Probability divergence** - Highlights arbitrage opportunities
3. **Hot topics** - Shows trending markets
4. **Data quality checks** - Proves reliability
5. **Crypto price correlation** - Shows multi-source integration

These queries demonstrate the power of the aggregated data!
