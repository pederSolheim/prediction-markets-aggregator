# Deployment Guide - Step by Step

This guide walks you through deploying the Prediction Markets Aggregator from scratch.

## 📋 Pre-Deployment Checklist

- [ ] Supabase account created
- [ ] Kalshi account registered (free)
- [ ] Opinion.trade account registered (free)
- [ ] Railway or Render account created (free)
- [ ] GitHub account (optional but recommended)

---

## Step 1: Set Up Supabase (10 minutes)

### 1.1 Create Project
1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose a name: `andurin-prediction-markets`
4. Set a strong database password (save it!)
5. Select a region close to your users
6. Click "Create new project" (takes 2-3 minutes)

### 1.2 Run Schema
1. Once project is ready, click "SQL Editor" in left sidebar
2. Click "New Query"
3. Copy entire contents of `schema.sql`
4. Paste into editor
5. Click "Run" button
6. You should see success message

### 1.3 Verify Tables
Run this query to verify:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

You should see:
- `prediction_markets_raw`
- `price_data`
- `sentiment_data`

### 1.4 Get API Credentials
1. Click "Settings" (gear icon) in left sidebar
2. Click "API" tab
3. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: Long string starting with `eyJ...`

---

## Step 2: Get API Keys (15 minutes)

### 2.1 Kalshi
1. Go to [kalshi.com](https://kalshi.com)
2. Click "Sign Up" (top right)
3. Complete registration with email
4. Verify email
5. Save your **email** and **password** (you'll use these as API credentials)

### 2.2 Opinion.trade
1. Go to [opinion.trade](https://opinion.trade)
2. Register for account
3. Go to Profile → API Settings
4. Generate API key
5. Save the **API key**

---

## Step 3: Test Locally (15 minutes)

### 3.1 Clone/Download Files
```bash
# If using git
git clone <your-repo>
cd prediction-markets-aggregator

# Or download and unzip the files
cd prediction-markets-aggregator
```

### 3.2 Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3.3 Set Up Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use any text editor
```

Fill in:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
KALSHI_EMAIL=your-email@example.com
KALSHI_PASSWORD=your-password
OPINION_API_KEY=your-api-key
```

### 3.4 Run Tests
```bash
python test_setup.py
```

All tests should pass. If not, fix issues before proceeding.

### 3.5 Test Data Collection
```bash
# Run once to test
python aggregator.py --once
```

Watch the logs. You should see:
- "Fetched X markets from Polymarket"
- "Fetched X markets from Kalshi"
- "Saved X markets to database"

### 3.6 Verify Data in Supabase
Go to Supabase → Table Editor → `prediction_markets_raw`

You should see rows with recent timestamps.

---

## Step 4: Deploy to Railway (Recommended) (10 minutes)

### 4.1 Push to GitHub
```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/yourusername/prediction-markets-aggregator.git
git push -u origin main
```

### 4.2 Deploy on Railway
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect GitHub and select your repository
5. Railway auto-detects `railway.json`

### 4.3 Add Environment Variables
In Railway dashboard:
1. Click your service
2. Go to "Variables" tab
3. Click "New Variable"
4. Add each variable:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `KALSHI_EMAIL`
   - `KALSHI_PASSWORD`
   - `OPINION_API_KEY`
5. Click "Deploy" to restart with new variables

### 4.4 Monitor Logs
1. Go to "Deployments" tab
2. Click latest deployment
3. View logs in real-time
4. Should see: "Starting scheduled collection every 15 minutes"

---

## Alternative: Deploy to Render (10 minutes)

### 4.1 Deploy on Render
1. Go to [render.com](https://render.com)
2. Click "New +"
3. Select "Background Worker"
4. Connect GitHub repository
5. Render auto-detects `render.yaml`

### 4.2 Configure
- **Name**: `prediction-markets-aggregator`
- **Environment**: Python 3
- **Build Command**: Auto-detected
- **Start Command**: Auto-detected

### 4.3 Add Environment Variables
Under "Environment" section, add all variables from `.env`

### 4.4 Deploy
Click "Create Background Worker"

Monitor logs in the dashboard.

---

## Step 5: Verify Production (24-48 hours)

### After 2 Hours
Check Supabase:
```sql
-- Should have ~8-10 collection cycles
SELECT COUNT(*) FROM prediction_markets_raw;

-- Check if all sources are working
SELECT source, COUNT(*) FROM prediction_markets_raw GROUP BY source;
```

### After 24 Hours
```sql
-- Should have ~96 collection cycles
SELECT COUNT(*) FROM prediction_markets_raw;

-- Check data distribution
SELECT 
    category,
    COUNT(*) as market_count,
    AVG(volume_usd) as avg_volume
FROM prediction_markets_raw
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY category;
```

### After 48 Hours
```sql
-- Full data verification
SELECT 
    source,
    category,
    COUNT(*) as records,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record
FROM prediction_markets_raw
GROUP BY source, category
ORDER BY source, category;
```

---

## Step 6: Set Up Monitoring (Optional)

### Email Alerts (Gmail)
1. Create Gmail App Password:
   - Go to Google Account Settings
   - Security → 2-Step Verification
   - App passwords → Generate
   
2. Add to Railway/Render environment variables:
```
ALERT_EMAIL_FROM=your-email@gmail.com
ALERT_EMAIL_TO=your-email@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

3. Redeploy

You'll get emails if:
- APIs fail
- Database saves fail
- Scheduler errors

---

## 📊 Expected Results After 48 Hours

### Data Volumes
- **Prediction Markets**: 1,000-5,000 records
  - Polymarket: 500-2,000
  - Kalshi: 300-1,500
  - Opinion: 200-1,500
- **Price Data**: 192 records (BTC + ETH)
- **Sentiment Data**: 96 records

### Collection Success Rate
- Target: >95% successful cycles
- If lower, check logs for API failures

---

## 🐛 Troubleshooting

### "No data being collected"
1. Check Railway/Render logs
2. Verify environment variables are set
3. Test APIs manually from deployment console
4. Check Supabase connection

### "Kalshi markets not appearing"
- Verify Kalshi credentials
- Login to Kalshi manually to confirm account works
- Check if account needs verification

### "Opinion markets missing"
- Opinion API structure may vary
- Check their current documentation
- Can disable temporarily in `config.yaml`

### "Railway/Render service crashed"
- Check logs for error message
- Verify all environment variables
- Check if free tier limits exceeded
- Restart service manually

---

## 🎉 Deployment Complete!

You now have:
- ✅ Automatic data collection every 15 minutes
- ✅ Historical data preserved permanently
- ✅ Multi-platform market aggregation
- ✅ Configurable keyword matching
- ✅ Cloud-deployed and running 24/7

---

## 📝 Next Steps for Job Application

1. **Take screenshots**:
   - Supabase dashboard showing data
   - Railway/Render deployment logs
   - Query results showing 48h of data

2. **Document your work**:
   - Write brief summary of implementation
   - Highlight configurable design
   - Note any improvements you made

3. **Prepare demo**:
   - Show keyword configuration
   - Show data queries
   - Explain scalability

4. **Include in proposal**:
   - GitHub repository link
   - Screenshots of working system
   - Brief technical writeup
   - Your timeline: "Completed in X days"

Good luck with your application! 🚀
