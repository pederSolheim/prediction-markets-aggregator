-- Prediction Markets Aggregator - Supabase Schema
-- Run this SQL in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: Prediction Markets Data
CREATE TABLE IF NOT EXISTS prediction_markets_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL CHECK (source IN ('polymarket', 'kalshi', 'opinion')),
    market_id TEXT NOT NULL,
    question TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('macro', 'crypto', 'geopolitics', 'politics', 'companies')),
    topic_tag TEXT NOT NULL,
    probability FLOAT NOT NULL CHECK (probability >= 0 AND probability <= 1),
    volume_usd FLOAT NOT NULL CHECK (volume_usd >= 0),
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_markets_source ON prediction_markets_raw(source);
CREATE INDEX IF NOT EXISTS idx_markets_category ON prediction_markets_raw(category);
CREATE INDEX IF NOT EXISTS idx_markets_topic_tag ON prediction_markets_raw(topic_tag);
CREATE INDEX IF NOT EXISTS idx_markets_timestamp ON prediction_markets_raw(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_markets_created_at ON prediction_markets_raw(created_at DESC);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_markets_category_timestamp ON prediction_markets_raw(category, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_markets_topic_timestamp ON prediction_markets_raw(topic_tag, timestamp DESC);

-- Table 2: Crypto Price Data
CREATE TABLE IF NOT EXISTS price_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset TEXT NOT NULL CHECK (asset IN ('BTC', 'ETH')),
    price_usd FLOAT NOT NULL CHECK (price_usd > 0),
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_price_asset ON price_data(asset);
CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_price_asset_timestamp ON price_data(asset, timestamp DESC);

-- Table 3: Sentiment Data (Fear & Greed Index)
CREATE TABLE IF NOT EXISTS sentiment_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fear_greed_value INTEGER NOT NULL CHECK (fear_greed_value >= 0 AND fear_greed_value <= 100),
    fear_greed_label TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sentiment_timestamp ON sentiment_data(timestamp DESC);

-- Optional: Create views for easier querying

-- View: Latest market data by topic
CREATE OR REPLACE VIEW latest_markets_by_topic AS
SELECT DISTINCT ON (topic_tag, source)
    source,
    market_id,
    question,
    category,
    topic_tag,
    probability,
    volume_usd,
    timestamp
FROM prediction_markets_raw
ORDER BY topic_tag, source, timestamp DESC;

-- View: Latest crypto prices
CREATE OR REPLACE VIEW latest_crypto_prices AS
SELECT DISTINCT ON (asset)
    asset,
    price_usd,
    timestamp
FROM price_data
ORDER BY asset, timestamp DESC;

-- View: Latest Fear & Greed
CREATE OR REPLACE VIEW latest_sentiment AS
SELECT
    fear_greed_value,
    fear_greed_label,
    timestamp
FROM sentiment_data
ORDER BY timestamp DESC
LIMIT 1;

-- View: Market comparison across platforms
CREATE OR REPLACE VIEW market_comparison AS
SELECT
    topic_tag,
    category,
    COUNT(DISTINCT source) as platform_count,
    AVG(probability) as avg_probability,
    SUM(volume_usd) as total_volume,
    MAX(timestamp) as latest_update
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY topic_tag, category
HAVING COUNT(DISTINCT source) > 1
ORDER BY total_volume DESC;

-- Comments for documentation
COMMENT ON TABLE prediction_markets_raw IS 'Raw prediction market data from Polymarket, Kalshi, and Opinion.trade';
COMMENT ON TABLE price_data IS 'Bitcoin and Ethereum price data from CoinGecko';
COMMENT ON TABLE sentiment_data IS 'Fear & Greed Index from alternative.me';

COMMENT ON COLUMN prediction_markets_raw.timestamp IS 'CRITICAL: Exact UTC timestamp when data was collected';
COMMENT ON COLUMN price_data.timestamp IS 'CRITICAL: Exact UTC timestamp when price was collected';
COMMENT ON COLUMN sentiment_data.timestamp IS 'CRITICAL: Exact UTC timestamp when sentiment was collected';

-- Grant necessary permissions (adjust as needed for your Supabase setup)
-- These are typically handled automatically by Supabase, but included for reference

-- Optional: Row Level Security (RLS) policies
-- Uncomment and modify if you need user-specific access control

-- ALTER TABLE prediction_markets_raw ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE price_data ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sentiment_data ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Enable read access for all users" ON prediction_markets_raw FOR SELECT USING (true);
-- CREATE POLICY "Enable read access for all users" ON price_data FOR SELECT USING (true);
-- CREATE POLICY "Enable read access for all users" ON sentiment_data FOR SELECT USING (true);

-- Verification query - run this to confirm tables were created
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE tablename IN ('prediction_markets_raw', 'price_data', 'sentiment_data');

-- Count rows in each table
SELECT 
    'prediction_markets_raw' as table_name,
    COUNT(*) as row_count
FROM prediction_markets_raw
UNION ALL
SELECT 
    'price_data' as table_name,
    COUNT(*) as row_count
FROM price_data
UNION ALL
SELECT 
    'sentiment_data' as table_name,
    COUNT(*) as row_count
FROM sentiment_data;
