#!/usr/bin/env python3
"""
Prediction Markets Aggregator
Collects data from multiple prediction market platforms and stores in Supabase
"""

import os
import sys
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import yaml
import requests
from supabase import create_client, Client
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aggregator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PredictionMarketsAggregator:
    """Main aggregator class for collecting prediction market data"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize the aggregator with configuration"""
        self.config = self._load_config(config_path)
        self.supabase = self._init_supabase()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'PredictionMarketsAggregator/1.0'})
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
            
    def _init_supabase(self) -> Client:
        """Initialize Supabase client"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")
            
        return create_client(url, key)
    
    def _get_utc_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()
    
    def _match_category_and_tag(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Match question text to category and extract topic tag
        Returns: (category, topic_tag) or (None, None)
        """
        question_lower = question.lower()
        
        for category, config in self.config['categories'].items():
            for keyword in config['keywords']:
                if keyword.lower() in question_lower:
                    # Use first matched keyword as topic tag (lowercase, underscored)
                    topic_tag = keyword.lower().replace(' ', '_').replace('&', 'and')
                    return category, topic_tag
                    
        return None, None
    
    def _send_alert_email(self, subject: str, body: str):
        """Send email alert on failure"""
        if not self.config.get('monitoring', {}).get('email_alerts', False):
            return
            
        try:
            from_email = os.getenv('ALERT_EMAIL_FROM')
            to_email = os.getenv('ALERT_EMAIL_TO')
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            if not all([from_email, to_email, smtp_host, smtp_user, smtp_password]):
                logger.warning("Email alert credentials not configured")
                return
                
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = f"[Andurin Alert] {subject}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
                
            logger.info(f"Alert email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
    
    # ==================== POLYMARKET ====================
    
    def fetch_polymarket_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets from Polymarket API"""
        if not self.config['apis']['polymarket']['enabled']:
            logger.info("Polymarket API disabled in config")
            return []
            
        markets_data = []
        timestamp = self._get_utc_timestamp()
        
        try:
            # Get all active markets
            url = f"{self.config['apis']['polymarket']['base_url']}/markets"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets from Polymarket")
            
            for market in markets:
                try:
                    question = market.get('question', '')
                    if not question:
                        continue
                    
                    # Match category and tag
                    category, topic_tag = self._match_category_and_tag(question)
                    if not category:
                        continue
                    
                    # Get volume
                    volume = float(market.get('volume', 0))
                    min_volume = self.config['categories'][category]['min_volume_usd']
                    
                    if volume < min_volume:
                        continue
                    
                    # Get probability (best offer price)
                    tokens = market.get('tokens', [])
                    probability = None
                    if tokens:
                        # Usually first token is the "Yes" outcome
                        best_bid = tokens[0].get('price')
                        if best_bid:
                            probability = float(best_bid)
                    
                    if probability is None:
                        probability = 0.5  # Default if not available
                    
                    markets_data.append({
                        'source': 'polymarket',
                        'market_id': market.get('condition_id', market.get('id', '')),
                        'question': question,
                        'category': category,
                        'topic_tag': topic_tag,
                        'probability': probability,
                        'volume_usd': volume,
                        'timestamp': timestamp
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing Polymarket market: {e}")
                    continue
                    
            logger.info(f"Collected {len(markets_data)} markets from Polymarket after filtering")
            
        except Exception as e:
            logger.error(f"Failed to fetch Polymarket markets: {e}")
            self._send_alert_email("Polymarket API Failed", f"Error: {str(e)}")
            
        return markets_data
    
    # ==================== KALSHI ====================
    
    def _kalshi_login(self) -> Optional[str]:
        """Login to Kalshi and get auth token"""
        try:
            email = os.getenv('KALSHI_EMAIL')
            password = os.getenv('KALSHI_PASSWORD')
            
            if not email or not password:
                logger.warning("Kalshi credentials not configured")
                return None
            
            url = f"{self.config['apis']['kalshi']['base_url']}/login"
            response = self.session.post(
                url,
                json={'email': email, 'password': password},
                timeout=30
            )
            response.raise_for_status()
            
            token = response.json().get('token')
            logger.info("Successfully logged in to Kalshi")
            return token
            
        except Exception as e:
            logger.error(f"Kalshi login failed: {e}")
            return None
    
    def fetch_kalshi_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets from Kalshi API"""
        if not self.config['apis']['kalshi']['enabled']:
            logger.info("Kalshi API disabled in config")
            return []
            
        markets_data = []
        timestamp = self._get_utc_timestamp()
        
        try:
            token = self._kalshi_login()
            if not token:
                return []
            
            headers = {'Authorization': f'Bearer {token}'}
            
            # Get all active markets
            url = f"{self.config['apis']['kalshi']['base_url']}/markets"
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            markets = data.get('markets', [])
            logger.info(f"Fetched {len(markets)} markets from Kalshi")
            
            for market in markets:
                try:
                    # Only active markets
                    if market.get('status') != 'active':
                        continue
                    
                    question = market.get('title', '')
                    if not question:
                        continue
                    
                    category, topic_tag = self._match_category_and_tag(question)
                    if not category:
                        continue
                    
                    # Get volume (in cents, convert to USD)
                    volume = float(market.get('volume', 0)) / 100.0
                    min_volume = self.config['categories'][category]['min_volume_usd']
                    
                    if volume < min_volume:
                        continue
                    
                    # Get probability (last price for Yes)
                    probability = float(market.get('yes_bid', 50)) / 100.0
                    
                    markets_data.append({
                        'source': 'kalshi',
                        'market_id': market.get('ticker', market.get('id', '')),
                        'question': question,
                        'category': category,
                        'topic_tag': topic_tag,
                        'probability': probability,
                        'volume_usd': volume,
                        'timestamp': timestamp
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing Kalshi market: {e}")
                    continue
                    
            logger.info(f"Collected {len(markets_data)} markets from Kalshi after filtering")
            
        except Exception as e:
            logger.error(f"Failed to fetch Kalshi markets: {e}")
            self._send_alert_email("Kalshi API Failed", f"Error: {str(e)}")
            
        return markets_data
    
    # ==================== OPINION ====================
    
    def fetch_opinion_markets(self) -> List[Dict[str, Any]]:
        """Fetch markets from Opinion.trade API"""
        if not self.config['apis']['opinion']['enabled']:
            logger.info("Opinion API disabled in config")
            return []
            
        markets_data = []
        timestamp = self._get_utc_timestamp()
        
        try:
            api_key = os.getenv('OPINION_API_KEY')
            if not api_key:
                logger.warning("Opinion API key not configured")
                return []
            
            headers = {'X-API-Key': api_key}
            
            # Note: Opinion.trade API endpoint may vary - adjust as needed
            url = f"{self.config['apis']['opinion']['base_url']}/markets"
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets from Opinion")
            
            for market in markets:
                try:
                    question = market.get('question', market.get('title', ''))
                    if not question:
                        continue
                    
                    category, topic_tag = self._match_category_and_tag(question)
                    if not category:
                        continue
                    
                    volume = float(market.get('volume', 0))
                    min_volume = self.config['categories'][category]['min_volume_usd']
                    
                    if volume < min_volume:
                        continue
                    
                    # Get probability
                    probability = float(market.get('probability', 0.5))
                    
                    markets_data.append({
                        'source': 'opinion',
                        'market_id': str(market.get('id', '')),
                        'question': question,
                        'category': category,
                        'topic_tag': topic_tag,
                        'probability': probability,
                        'volume_usd': volume,
                        'timestamp': timestamp
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing Opinion market: {e}")
                    continue
                    
            logger.info(f"Collected {len(markets_data)} markets from Opinion after filtering")
            
        except Exception as e:
            logger.error(f"Failed to fetch Opinion markets: {e}")
            self._send_alert_email("Opinion API Failed", f"Error: {str(e)}")
            
        return markets_data
    
    # ==================== FEAR & GREED INDEX ====================
    
    def fetch_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """Fetch Fear & Greed Index"""
        if not self.config['apis']['fear_greed']['enabled']:
            logger.info("Fear & Greed API disabled in config")
            return None
            
        try:
            url = self.config['apis']['fear_greed']['base_url']
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            current = data['data'][0]
            
            return {
                'fear_greed_value': int(current['value']),
                'fear_greed_label': current['value_classification'],
                'timestamp': self._get_utc_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch Fear & Greed Index: {e}")
            self._send_alert_email("Fear & Greed API Failed", f"Error: {str(e)}")
            return None
    
    # ==================== COINGECKO ====================
    
    def fetch_crypto_prices(self) -> List[Dict[str, Any]]:
        """Fetch BTC and ETH prices from CoinGecko"""
        if not self.config['apis']['coingecko']['enabled']:
            logger.info("CoinGecko API disabled in config")
            return []
            
        prices_data = []
        timestamp = self._get_utc_timestamp()
        
        try:
            url = f"{self.config['apis']['coingecko']['base_url']}/simple/price"
            params = {
                'ids': 'bitcoin,ethereum',
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'bitcoin' in data:
                prices_data.append({
                    'asset': 'BTC',
                    'price_usd': float(data['bitcoin']['usd']),
                    'timestamp': timestamp
                })
                
            if 'ethereum' in data:
                prices_data.append({
                    'asset': 'ETH',
                    'price_usd': float(data['ethereum']['usd']),
                    'timestamp': timestamp
                })
                
            logger.info(f"Fetched {len(prices_data)} crypto prices")
            
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")
            self._send_alert_email("CoinGecko API Failed", f"Error: {str(e)}")
            
        return prices_data
    
    # ==================== DATABASE OPERATIONS ====================
    
    def save_markets_to_db(self, markets: List[Dict[str, Any]]):
        """Save prediction markets data to Supabase"""
        if not markets:
            logger.info("No markets to save")
            return
            
        try:
            # Insert in batches
            batch_size = self.config['database']['batch_size']
            for i in range(0, len(markets), batch_size):
                batch = markets[i:i+batch_size]
                self.supabase.table('prediction_markets_raw').insert(batch).execute()
                logger.info(f"Saved batch of {len(batch)} markets to database")
                
            logger.info(f"Successfully saved {len(markets)} markets to database")
            
        except Exception as e:
            logger.error(f"Failed to save markets to database: {e}")
            self._send_alert_email("Database Save Failed - Markets", f"Error: {str(e)}")
    
    def save_prices_to_db(self, prices: List[Dict[str, Any]]):
        """Save crypto prices to Supabase"""
        if not prices:
            logger.info("No prices to save")
            return
            
        try:
            self.supabase.table('price_data').insert(prices).execute()
            logger.info(f"Saved {len(prices)} crypto prices to database")
            
        except Exception as e:
            logger.error(f"Failed to save prices to database: {e}")
            self._send_alert_email("Database Save Failed - Prices", f"Error: {str(e)}")
    
    def save_sentiment_to_db(self, sentiment: Dict[str, Any]):
        """Save Fear & Greed Index to Supabase"""
        if not sentiment:
            logger.info("No sentiment data to save")
            return
            
        try:
            self.supabase.table('sentiment_data').insert(sentiment).execute()
            logger.info("Saved Fear & Greed Index to database")
            
        except Exception as e:
            logger.error(f"Failed to save sentiment to database: {e}")
            self._send_alert_email("Database Save Failed - Sentiment", f"Error: {str(e)}")
    
    # ==================== MAIN COLLECTION LOOP ====================
    
    def collect_all_data(self):
        """Main function to collect all data from all sources"""
        logger.info("=" * 60)
        logger.info("Starting data collection cycle")
        logger.info("=" * 60)
        
        start_time = time.time()
        all_markets = []
        
        # Collect from all prediction market sources
        try:
            polymarket_markets = self.fetch_polymarket_markets()
            all_markets.extend(polymarket_markets)
        except Exception as e:
            logger.error(f"Polymarket collection failed: {e}")
        
        try:
            kalshi_markets = self.fetch_kalshi_markets()
            all_markets.extend(kalshi_markets)
        except Exception as e:
            logger.error(f"Kalshi collection failed: {e}")
        
        try:
            opinion_markets = self.fetch_opinion_markets()
            all_markets.extend(opinion_markets)
        except Exception as e:
            logger.error(f"Opinion collection failed: {e}")
        
        # Save prediction markets
        if all_markets:
            self.save_markets_to_db(all_markets)
        
        # Collect crypto prices
        try:
            prices = self.fetch_crypto_prices()
            if prices:
                self.save_prices_to_db(prices)
        except Exception as e:
            logger.error(f"Crypto prices collection failed: {e}")
        
        # Collect Fear & Greed Index
        try:
            sentiment = self.fetch_fear_greed_index()
            if sentiment:
                self.save_sentiment_to_db(sentiment)
        except Exception as e:
            logger.error(f"Fear & Greed collection failed: {e}")
        
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"Collection cycle completed in {elapsed:.2f} seconds")
        logger.info(f"Total markets collected: {len(all_markets)}")
        logger.info("=" * 60)
    
    def run_scheduled(self):
        """Run the collector on a schedule"""
        interval = self.config['schedule']['interval_minutes']
        logger.info(f"Starting scheduled collection every {interval} minutes")
        
        # Run once immediately
        try:
            self.collect_all_data()
        except Exception as e:
            logger.error(f"Initial collection failed: {e}")
            self._send_alert_email("Initial Collection Failed", f"Error: {str(e)}")
        
        # Schedule recurring runs
        schedule.every(interval).minutes.do(self.collect_all_data)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self._send_alert_email("Scheduler Error", f"Error: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying


def main():
    """Main entry point"""
    try:
        aggregator = PredictionMarketsAggregator()
        
        # Check if running once or scheduled
        if len(sys.argv) > 1 and sys.argv[1] == '--once':
            logger.info("Running one-time collection")
            aggregator.collect_all_data()
        else:
            logger.info("Running in scheduled mode")
            aggregator.run_scheduled()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
