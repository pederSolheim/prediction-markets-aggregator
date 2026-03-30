# Prediction Markets Aggregator

A Python data pipeline that collects real-time prediction market data from Polymarket, Kalshi, and Opinion.trade, along with crypto prices and Fear & Greed Index, storing everything in Supabase.

## 🎯 Features

- **Multi-source data collection**: Polymarket, Kalshi, Opinion.trade
- **Configurable keyword matching**: Edit categories and keywords without touching code
- **Automatic categorization**: Markets auto-tagged by category (macro/crypto/geopolitics/politics/companies)
- **Volume filtering**: Configurable minimum volume thresholds per category
- **Append-only database**: Never overwrites historical data
- **UTC timestamps**: Precise timestamps on every record
- **Graceful error handling**: Continues if one API fails
- **Email alerts**: Optional monitoring via email
- **Scheduled execution**: Runs every 15 minutes automatically
- **Cloud deployment**: Ready for Railway or Render

## 📋 Prerequisites

1. **Supabase account** (free tier works)
2. **Kalshi account** (free registration at trading-api.kalshi.com)
3. **Opinion.trade account** (free registration)
4. **Railway or Render account** (free tier works)

## 🚀 Quick Start

### 1. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the entire `schema.sql` file
3. Go to Settings → API to get your:
   - Project URL (e.g., `https://xxx.supabase.co`)
   - Anon/Public key

### 2. Get API Credentials

**Kalshi:**
- Register at [kalshi.com](https://kalshi.com)
- Use your email and password

**Opinion.trade:**
- Register at [opinion.trade](https://opinion.trade)
- Get API key from account settings

### 3. Configure Locally (for testing)

```bash
# Clone or download this project
cd prediction-markets-aggregator

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 4. Test Locally

```bash
# Run once to test
python aggregator.py --once

# Run in scheduled mode (every 15 minutes)
python aggregator.py
```

## ⚙️ Configuration

### Editing Keywords (config.yaml)

The `config.yaml` file controls which markets are collected. You can edit this file without touching any Python code.

**To add a keyword:**

```yaml
categories:
  crypto:
    keywords:
      - Bitcoin
      - BTC
      - Dogecoin  # ← Add this line
```

**To change minimum volume:**

```yaml
categories:
  crypto:
    min_volume_usd: 1000000  # Changed from 500000
```

**To add a new category:**

```yaml
categories:
  sports:  # New category
    keywords:
      - NBA
      - NFL
      - Super Bowl
    min_volume_usd: 50000
```

**Important:** After adding a new category, update `schema.sql` to include it in the CHECK constraint:

```sql
category TEXT NOT NULL CHECK (category IN ('macro', 'crypto', 'geopolitics', 'politics', 'companies', 'sports'))
```

### Disabling Data Sources

To temporarily disable a data source:

```yaml
apis:
  polymarket:
    enabled: false  # Changed from true
```

## 🚢 Deployment

### Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub and select this repository
4. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `KALSHI_EMAIL`
   - `KALSHI_PASSWORD`
   - `OPINION_API_KEY`
   - (Optional) Email alert variables
5. Railway will automatically detect `railway.json` and deploy

### Deploy to Render

1. Go to [render.com](https://render.com)
2. Click "New" → "Background Worker"
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Add environment variables in the dashboard
6. Click "Create Background Worker"

## 📊 Database Schema

### prediction_markets_raw
- `id`: Auto-generated UUID
- `source`: polymarket / kalshi / opinion
- `market_id`: Unique ID from platform
- `question`: Full market question
- `category`: macro / crypto / geopolitics / politics / companies
- `topic_tag`: Matched keyword (e.g., 'fed', 'btc', 'iran')
- `probability`: Float 0-1
- `volume_usd`: Trading volume in USD
- `timestamp`: Exact UTC timestamp (CRITICAL)
- `created_at`: Auto-generated

### price_data
- `id`: Auto-generated UUID
- `asset`: BTC / ETH
- `price_usd`: Price in USD
- `timestamp`: Exact UTC timestamp
- `created_at`: Auto-generated

### sentiment_data
- `id`: Auto-generated UUID
- `fear_greed_value`: 0-100
- `fear_greed_label`: Text classification
- `timestamp`: Exact UTC timestamp
- `created_at`: Auto-generated

## 📈 Querying the Data

### Get latest markets by topic
```sql
SELECT * FROM latest_markets_by_topic WHERE topic_tag = 'btc';
```

### Compare same topic across platforms
```sql
SELECT * FROM market_comparison WHERE topic_tag = 'fed' ORDER BY latest_update DESC;
```

### Get crypto price history
```sql
SELECT * FROM price_data WHERE asset = 'BTC' ORDER BY timestamp DESC LIMIT 100;
```

### Markets by category in last 24 hours
```sql
SELECT 
    category,
    COUNT(*) as market_count,
    AVG(volume_usd) as avg_volume,
    AVG(probability) as avg_probability
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY category;
```

## 🔍 Monitoring

### Check Logs

**Locally:**
```bash
tail -f aggregator.log
```

**Railway:**
- Go to your service → View Logs

**Render:**
- Go to your service → Logs tab

### Email Alerts

Configure email alerts in `.env`:

```env
ALERT_EMAIL_FROM=alerts@andurin.ai
ALERT_EMAIL_TO=your-email@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

Alerts are sent when:
- API calls fail
- Database operations fail
- Scheduler encounters errors

## 🧪 Testing

### Verify Data Collection

After 48 hours, run these queries in Supabase:

```sql
-- Check total records
SELECT COUNT(*) FROM prediction_markets_raw;

-- Records per source
SELECT source, COUNT(*) FROM prediction_markets_raw GROUP BY source;

-- Records per category
SELECT category, COUNT(*) FROM prediction_markets_raw GROUP BY category;

-- Recent data
SELECT * FROM prediction_markets_raw ORDER BY timestamp DESC LIMIT 10;
```

### Expected Results

With 15-minute intervals over 48 hours:
- 96 collection cycles (48 hours × 4 per hour)
- ~10-50 markets per cycle (depends on active markets)
- ~1000-5000 total market records after 48 hours
- 192 price records (BTC + ETH × 96 cycles)
- 96 sentiment records

## 🐛 Troubleshooting

### "No markets collected"
- Check if keywords match active markets on the platforms
- Lower the `min_volume_usd` thresholds temporarily
- Check API status at the provider websites

### "Kalshi login failed"
- Verify credentials in environment variables
- Check if Kalshi API is accessible from your deployment region

### "Database connection failed"
- Verify `SUPABASE_URL` and `SUPABASE_KEY`
- Check if Supabase project is active
- Ensure tables were created with `schema.sql`

### "Opinion API not working"
- Opinion.trade API endpoints may have changed
- Check their documentation for current API structure
- You can disable it temporarily in `config.yaml`

## 📝 API Notes

### Polymarket
- Public API, no authentication needed
- Endpoint: `https://clob.polymarket.com/markets`
- Returns all active markets

### Kalshi
- Requires free account
- Login returns bearer token
- Token valid for session

### Opinion.trade
- Requires API key
- API structure may vary - adjust code if needed

### Fear & Greed Index
- Public API
- Updates once per day
- Values 0-100 with text classification

### CoinGecko
- Public API
- Free tier: 50 calls/minute
- We only call once per cycle

## 🔐 Security

- Never commit `.env` file
- Use environment variables for all secrets
- Rotate API keys periodically
- Use Supabase Row Level Security (RLS) if exposing data

## 📄 License

This is a job application project. Modify as needed.

## 🤝 Support

For issues or questions:
1. Check logs first (`aggregator.log`)
2. Verify environment variables
3. Test APIs individually with `--once` flag
4. Check Supabase table permissions

## 🎉 Success Checklist

- [ ] Supabase tables created with `schema.sql`
- [ ] All environment variables configured
- [ ] Script runs locally without errors
- [ ] Deployed to Railway or Render
- [ ] Email alerts working (optional)
- [ ] 48 hours of data collected
- [ ] Data queryable in Supabase

---

**Built for Andurin.ai prediction markets intelligence platform**
