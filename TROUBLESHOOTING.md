# Troubleshooting Guide

Common issues and their solutions when setting up the Prediction Markets Aggregator.

## 🔴 Installation & Setup Issues

### "ModuleNotFoundError: No module named 'supabase'"

**Problem**: Python dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt

# If that fails, install individually:
pip install requests==2.31.0
pip install supabase==2.3.4
pip install pyyaml==6.0.1
pip install schedule==1.2.1
```

### "ValueError: SUPABASE_URL and SUPABASE_KEY environment variables required"

**Problem**: Environment variables not set

**Solution (Linux/Mac)**:
```bash
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="eyJhbGc..."
```

**Solution (Windows CMD)**:
```cmd
set SUPABASE_URL=https://xxx.supabase.co
set SUPABASE_KEY=eyJhbGc...
```

**Solution (Windows PowerShell)**:
```powershell
$env:SUPABASE_URL="https://xxx.supabase.co"
$env:SUPABASE_KEY="eyJhbGc..."
```

**Better solution**: Create a `.env` file:
```bash
cp .env.example .env
# Then edit .env with your values
```

Then modify aggregator.py to load from .env:
```python
from dotenv import load_dotenv
load_dotenv()  # Add this at the top of the file
```

### "yaml.scanner.ScannerError: mapping values are not allowed here"

**Problem**: Syntax error in config.yaml

**Solution**:
- Check for proper indentation (use spaces, not tabs)
- Make sure colons have spaces after them: `key: value` not `key:value`
- Quote values with special characters: `keyword: "2026"`
- Check for missing or extra colons

**Validate your YAML**:
```python
import yaml
with open('config.yaml') as f:
    yaml.safe_load(f)  # Will show exact error line
```

## 🔴 Database Issues

### "relation 'prediction_markets_raw' does not exist"

**Problem**: Database tables not created

**Solution**:
1. Go to Supabase SQL Editor
2. Copy entire `schema.sql` file
3. Paste and click "Run"
4. Verify with:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

### "new row violates check constraint"

**Problem**: Data doesn't match schema constraints

**Common causes**:
- Probability not between 0 and 1
- Invalid category name
- Invalid source name
- Negative volume

**Solution**: Check the logs for which field is invalid:
```bash
tail -n 50 aggregator.log | grep "constraint"
```

### "duplicate key value violates unique constraint"

**Problem**: Trying to insert duplicate primary key

**Solution**: This shouldn't happen with UUID auto-generation. If it does:
```sql
-- Check for duplicates
SELECT market_id, source, timestamp, COUNT(*) 
FROM prediction_markets_raw 
GROUP BY market_id, source, timestamp 
HAVING COUNT(*) > 1;
```

### "connection timeout" or "could not connect to server"

**Problem**: Supabase connection issue

**Solutions**:
1. Check Supabase project is active (not paused)
2. Verify SUPABASE_URL is correct (should start with https://)
3. Verify SUPABASE_KEY is the anon/public key, not the service key
4. Check your internet connection
5. Try the Supabase dashboard - if that doesn't load, their service might be down

## 🔴 API Issues

### "Polymarket: Failed to fetch markets: 403 Forbidden"

**Problem**: Rate limited or blocked

**Solutions**:
1. Wait 5-10 minutes and try again
2. Check if Polymarket API is down: https://status.polymarket.com
3. Try from different IP (rate limits are per IP)
4. Add delay between requests:
```python
time.sleep(2)  # Add in the fetch function
```

### "Kalshi login failed: 401 Unauthorized"

**Problem**: Invalid credentials

**Solutions**:
1. Verify email/password are correct
2. Try logging in manually at kalshi.com
3. Reset password if needed
4. Check for typos in environment variables:
```bash
echo $KALSHI_EMAIL
echo $KALSHI_PASSWORD
```
5. Make sure no extra spaces in .env file

### "Kalshi login failed: 429 Too Many Requests"

**Problem**: Too many login attempts

**Solution**:
- Wait 15-30 minutes before retrying
- The script logs in once per collection cycle, so this shouldn't happen
- If it persists, contact Kalshi support

### "Opinion API: 404 Not Found"

**Problem**: API endpoint has changed

**Solution**:
1. Check Opinion.trade documentation for current endpoints
2. They may have changed their API structure
3. Temporarily disable in config.yaml:
```yaml
apis:
  opinion:
    enabled: false
```
4. Update the base_url in config.yaml once you find the correct endpoint

### "CoinGecko: 429 Too Many Requests"

**Problem**: Hit free tier rate limit (50 calls/minute)

**Solution**:
- This shouldn't happen (we only call once per 15 min)
- If using multiple scripts, they share the rate limit
- Wait 1 minute and it will auto-retry
- Consider upgrading to CoinGecko Pro if running multiple instances

### "Fear & Greed: SSL certificate verification failed"

**Problem**: HTTPS certificate issue

**Solution**:
```python
# In aggregator.py, modify the request:
response = self.session.get(url, timeout=30, verify=False)
# Note: Only use verify=False for testing, not production
```

Better solution - update your SSL certificates:
```bash
pip install --upgrade certifi
```

## 🔴 Data Collection Issues

### "No markets collected" or "0 markets after filtering"

**Problem**: No markets match your keywords or volume thresholds

**Solutions**:
1. **Lower volume thresholds** in config.yaml:
```yaml
crypto:
  min_volume_usd: 10000  # Instead of 500000
```

2. **Add more keywords**:
```yaml
crypto:
  keywords:
    - Bitcoin
    - BTC
    - crypto  # Very broad keyword
```

3. **Check what's available**:
```python
# Temporarily add this to see all markets:
print(f"Total markets before filtering: {len(markets)}")
for market in markets[:5]:
    print(f"Question: {market.get('question')}")
    print(f"Volume: {market.get('volume')}")
```

4. **Test individual APIs**:
```bash
# Run once to see detailed logs
python aggregator.py --once
```

### "Collected X markets but none saved to database"

**Problem**: Database save failing silently

**Solution**:
1. Check logs for database errors:
```bash
grep -i "database\|error\|failed" aggregator.log
```

2. Verify Supabase connection:
```python
python test_setup.py
```

3. Test manual insert:
```sql
-- In Supabase SQL Editor
INSERT INTO prediction_markets_raw (source, market_id, question, category, topic_tag, probability, volume_usd, timestamp)
VALUES ('test', 'test123', 'Test question?', 'crypto', 'btc', 0.5, 100000, NOW());
```

### "Same markets appearing multiple times"

**Problem**: This is expected! The script appends every 15 minutes

**Verification**:
```sql
SELECT market_id, source, COUNT(*) as appearances
FROM prediction_markets_raw
GROUP BY market_id, source
ORDER BY appearances DESC;
```

High count = market is stable and being tracked correctly

## 🔴 Deployment Issues

### Railway: "Build failed" or "Deployment failed"

**Problem**: Build or runtime error

**Solutions**:
1. Check Railway logs for specific error
2. Verify all files are in repository:
```bash
git status
git add .
git commit -m "Add missing files"
git push
```

3. Make sure requirements.txt is at root level
4. Check Dockerfile syntax
5. Verify railway.json is valid JSON

### Railway: "Application crashed" or keeps restarting

**Problem**: Runtime error

**Solutions**:
1. Check environment variables are set in Railway dashboard
2. View logs in Railway for the error message
3. Test locally first:
```bash
python aggregator.py --once
```

4. Common issue - missing environment variable:
```
Go to Railway → Variables → Add missing variable
```

### Render: "Service suspended" or "Service not responding"

**Problem**: Render free tier limitations

**Solutions**:
1. Free tier services sleep after 15 min of inactivity
2. This is okay! Render will wake it up
3. For 24/7 operation, upgrade to paid tier ($7/month)
4. Or use Railway instead (better free tier)

### "Out of memory" or "OOMKilled"

**Problem**: Using too much RAM

**Solutions**:
1. Reduce batch size in config.yaml:
```yaml
database:
  batch_size: 50  # Instead of 100
```

2. Process fewer markets at once
3. Upgrade to higher tier (Railway Pro, Render Standard)

## 🔴 Monitoring Issues

### "Email alerts not working"

**Problem**: SMTP configuration issue

**Solutions**:
1. Verify all SMTP variables are set
2. For Gmail, use App Password, not regular password:
   - Google Account → Security → 2-Step Verification → App passwords
3. Check SMTP port (587 for TLS, 465 for SSL)
4. Test SMTP connection:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print("SMTP connection successful!")
```

### "Logs not showing in Railway/Render"

**Problem**: Logs not configured correctly

**Solution**:
- Logs should automatically appear
- If not, check that you're using `print()` or `logging` (both go to stdout)
- Railway/Render capture stdout automatically

### "Can't tell if script is running"

**Problem**: No monitoring

**Solution**:
1. Check Railway/Render dashboard - should show "Running"
2. Look at Supabase table - timestamps should be updating every 15 min
3. Add a health check endpoint (advanced):
```python
# Add simple HTTP server to report status
```

## 🔴 Performance Issues

### "Script taking too long (>5 minutes per cycle)"

**Problem**: API calls timing out or database slow

**Solutions**:
1. Increase timeout values:
```python
response = self.session.get(url, timeout=60)  # Instead of 30
```

2. Check which API is slow:
```bash
grep "seconds" aggregator.log
```

3. Reduce number of markets:
```yaml
# Increase volume thresholds
crypto:
  min_volume_usd: 1000000  # Filter out more markets
```

### "Database inserts failing intermittently"

**Problem**: Network issues or Supabase rate limits

**Solutions**:
1. Add retry logic (already in code)
2. Reduce batch size
3. Check Supabase status: https://status.supabase.com
4. Verify you're not hitting free tier limits

## 🔴 Data Quality Issues

### "Timestamps not in UTC"

**Problem**: Timezone confusion

**Verification**:
```sql
SELECT timestamp, EXTRACT(TIMEZONE FROM timestamp) as tz
FROM prediction_markets_raw
LIMIT 5;
```

**Solution**: The code uses `datetime.now(timezone.utc)` which is correct

### "Probabilities over 1.0 or negative"

**Problem**: Bad data from API or conversion error

**Solution**:
```sql
-- Find bad probabilities
SELECT * FROM prediction_markets_raw
WHERE probability > 1.0 OR probability < 0;
```

Add validation in aggregator.py:
```python
probability = max(0.0, min(1.0, float(market.get('yes_bid', 50)) / 100.0))
```

### "Volume values seem wrong"

**Problem**: Currency conversion issue (cents vs dollars)

**Check**:
```sql
SELECT source, question, volume_usd
FROM prediction_markets_raw
WHERE volume_usd > 100000000  -- Over $100M seems suspicious
   OR volume_usd < 0;
```

**Solution**: Check the API response format for each platform

## 🔴 Test Script Issues

### "test_setup.py failing on Supabase connection"

**Problem**: Most likely credential issue

**Solution**:
1. Regenerate Supabase API key
2. Make sure using anon key, not service_role key
3. Check project is active
4. Try connection manually:
```python
from supabase import create_client
client = create_client('your-url', 'your-key')
result = client.table('prediction_markets_raw').select('*').limit(1).execute()
```

## 📞 Getting Help

If you're still stuck:

1. **Check logs first**: `tail -n 100 aggregator.log`
2. **Run test script**: `python test_setup.py`
3. **Test one API at a time**: Disable others in config.yaml
4. **Check external status**:
   - Supabase: https://status.supabase.com
   - Railway: https://railway.app/status
   - Render: https://status.render.com

## ✅ Verification Checklist

Use this to verify everything is working:

- [ ] test_setup.py passes all checks
- [ ] aggregator.py --once runs without errors
- [ ] Data appears in Supabase within 1 minute
- [ ] Timestamps are in UTC
- [ ] All 3 tables have data
- [ ] Logs show "Saved X markets to database"
- [ ] Scheduled run completes every 15 minutes
- [ ] No error emails received
- [ ] Data count increasing over time

## 🎯 Still Having Issues?

Create a GitHub issue with:
1. Full error message from logs
2. Which step you're stuck on
3. What you've already tried
4. Your environment (OS, Python version)

Most issues are environment variables or API credentials - double-check those first!
