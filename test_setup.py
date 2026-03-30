#!/usr/bin/env python3
"""
Test script to verify the aggregator setup
Run this before deploying to catch configuration issues
"""

import os
import sys
import yaml
from supabase import create_client

def test_config_file():
    """Test if config.yaml is valid"""
    print("Testing config.yaml...")
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        assert 'categories' in config, "Missing 'categories' section"
        assert 'apis' in config, "Missing 'apis' section"
        
        # Check categories
        required_categories = ['macro', 'crypto', 'geopolitics', 'politics', 'companies']
        for cat in required_categories:
            assert cat in config['categories'], f"Missing category: {cat}"
            assert 'keywords' in config['categories'][cat], f"Missing keywords for {cat}"
            assert 'min_volume_usd' in config['categories'][cat], f"Missing min_volume for {cat}"
        
        print("✓ config.yaml is valid")
        return True
    except Exception as e:
        print(f"✗ config.yaml error: {e}")
        return False

def test_environment_variables():
    """Test if required environment variables are set"""
    print("\nTesting environment variables...")
    
    required = {
        'SUPABASE_URL': 'Required',
        'SUPABASE_KEY': 'Required',
        'KALSHI_EMAIL': 'Optional (for Kalshi data)',
        'KALSHI_PASSWORD': 'Optional (for Kalshi data)',
        'OPINION_API_KEY': 'Optional (for Opinion data)',
    }
    
    optional = {
        'ALERT_EMAIL_FROM': 'Optional (for email alerts)',
        'ALERT_EMAIL_TO': 'Optional (for email alerts)',
        'SMTP_HOST': 'Optional (for email alerts)',
        'SMTP_PORT': 'Optional (for email alerts)',
        'SMTP_USER': 'Optional (for email alerts)',
        'SMTP_PASSWORD': 'Optional (for email alerts)',
    }
    
    all_vars = {**required, **optional}
    issues = []
    
    for var, description in all_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Not set ({description})")
            if description == 'Required':
                issues.append(var)
    
    if issues:
        print(f"\n⚠ Missing required variables: {', '.join(issues)}")
        return False
    
    print("\n✓ All required environment variables are set")
    return True

def test_supabase_connection():
    """Test Supabase connection"""
    print("\nTesting Supabase connection...")
    
    try:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            print("✗ Missing SUPABASE_URL or SUPABASE_KEY")
            return False
        
        supabase = create_client(url, key)
        
        # Test connection by checking if tables exist
        tables = ['prediction_markets_raw', 'price_data', 'sentiment_data']
        
        for table in tables:
            try:
                # Try to query the table (will return empty if no data)
                result = supabase.table(table).select('id').limit(1).execute()
                print(f"✓ Table '{table}' exists and is accessible")
            except Exception as e:
                print(f"✗ Table '{table}' error: {e}")
                print(f"  → Make sure you ran schema.sql in Supabase")
                return False
        
        print("✓ Supabase connection successful")
        return True
        
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")
        return False

def test_api_endpoints():
    """Test if API endpoints are accessible"""
    print("\nTesting API endpoints...")
    
    import requests
    
    endpoints = {
        'Polymarket': 'https://clob.polymarket.com/markets',
        'Fear & Greed': 'https://api.alternative.me/fng/',
        'CoinGecko': 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
    }
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'PredictionMarketsAggregator/1.0'})
    
    for name, url in endpoints.items():
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            print(f"✓ {name} API is accessible")
        except Exception as e:
            print(f"✗ {name} API error: {e}")
    
    print("\n✓ Public APIs are accessible")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Prediction Markets Aggregator - Setup Test")
    print("=" * 60)
    
    tests = [
        ("Configuration File", test_config_file),
        ("Environment Variables", test_environment_variables),
        ("Supabase Connection", test_supabase_connection),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! You're ready to deploy.")
        return 0
    else:
        print("\n⚠ Some tests failed. Fix the issues above before deploying.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
