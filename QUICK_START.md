# Quick Start Guide - 15 Minutes to Running

Get the prediction markets aggregator running in 15 minutes.

## 🎯 Prerequisites

- Python 3.9+ installed
- Supabase account (free)
- Kalshi account (free)
- Opinion.trade account (free)

## ⚡ Super Quick Setup

### 1. Database (5 minutes)

```bash
# Go to supabase.com → New Project
# In SQL Editor, paste entire schema.sql file → Run
# Settings → API → Copy URL and Key
```

### 2. Install & Configure (3 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (Linux/Mac)
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="eyJhbGc..."
export KALSHI_EMAIL="your-email@example.com"
export KALSHI_PASSWORD="your-password"
export OPINION_API_KEY="your-api-key"

# Or create .env file
cp .env.example .env
# Edit .env with your values
```

### 3. Test (2 minutes)

```bash
# Verify setup
python test_setup.py

# Run one collection cycle
python aggregator.py --once
```

### 4. Deploy to Railway (5 minutes)

```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/repo.git
git push -u origin main

# On railway.app:
# 1. New Project → Deploy from GitHub
# 2. Add environment variables
# 3. Done! It's running.
```

## 🔍 Verify It's Working

### Check Logs
```bash
# Locally
tail -f aggregator.log

# Railway
# Go to service → View Logs
```

### Check Database
```sql
-- In Supabase SQL Editor
SELECT COUNT(*) FROM prediction_markets_raw;
SELECT * FROM prediction_markets_raw ORDER BY timestamp DESC LIMIT 5;
```

## 📝 Quick Configuration Changes

### Add a keyword
```yaml
# Edit config.yaml
categories:
  crypto:
    keywords:
      - Bitcoin
      - Dogecoin  # ← Add this line
```

### Change volume threshold
```yaml
categories:
  crypto:
    min_volume_usd: 1000000  # Changed from 500000
```

### Disable a source
```yaml
apis:
  opinion:
    enabled: false  # Changed from true
```

## 🎉 You're Done!

The aggregator is now:
- ✅ Collecting data every 15 minutes
- ✅ Storing in Supabase permanently
- ✅ Running in the cloud 24/7

Check back in 24 hours and you'll have hundreds of market records!

## 🆘 Quick Troubleshooting

**No data collected?**
- Check `aggregator.log` for errors
- Verify API credentials in environment variables
- Test each API manually in `test_setup.py`

**Database errors?**
- Confirm `schema.sql` was run successfully
- Check Supabase URL and Key are correct
- Verify tables exist in Table Editor

**Deployment issues?**
- Check all environment variables are set
- View logs in Railway/Render dashboard
- Restart the service manually

---

For detailed guides, see:
- **README.md** - Complete documentation
- **DEPLOYMENT_GUIDE.md** - Step-by-step deployment
- **PROPOSAL_TEMPLATE.md** - Job application template
