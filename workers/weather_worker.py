"""
Weather worker - periodically fetches weather forecasts.
Simple scheduler-based worker (no Celery complexity for capstone).
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.weather import get_weather_service
from api.services.cache import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_weather_job():
    """Job to fetch and cache weather forecasts."""
    try:
        logger.info("Starting weather fetch job...")
        
        # Get Redis client
        redis_client = get_redis_client()
        
        # Get weather service
        weather_service = get_weather_service(redis_client)
        
        # Fetch next 48 hours (OpenWeatherMap free tier limit)
        cached_count = weather_service.fetch_and_cache_forecast(hours_ahead=48)
        
        logger.info(f"Weather fetch complete: {cached_count} hours cached")
    
    except Exception as e:
        logger.error(f"Weather fetch job failed: {e}", exc_info=True)


def run_worker(interval_minutes: int = 10):
    """
    Run weather worker with periodic fetching.
    
    Args:
        interval_minutes: Minutes between fetch attempts
    """
    logger.info(f"Weather worker started (interval: {interval_minutes} minutes)")
    logger.info(f"API Key configured: {bool(os.getenv('WEATHER_API_KEY'))}")
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'Not configured')}")
    
    # Run immediately on startup
    fetch_weather_job()
    
    # Then run periodically
    interval_seconds = interval_minutes * 60
    
    while True:
        try:
            time.sleep(interval_seconds)
            fetch_weather_job()
        
        except KeyboardInterrupt:
            logger.info("Weather worker stopped by user")
            break
        
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            # Continue running despite errors
            time.sleep(60)  # Wait 1 minute before retry


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Weather forecast worker')
    parser.add_argument(
        '--interval',
        type=int,
        default=10,
        help='Minutes between fetch attempts (default: 10)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (for testing)'
    )
    
    args = parser.parse_args()
    
    if args.once:
        logger.info("Running weather fetch once...")
        fetch_weather_job()
        logger.info("Done")
    else:
        run_worker(interval_minutes=args.interval)
