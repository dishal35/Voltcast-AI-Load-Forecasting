"""
Test weekly forecast endpoint.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.model_loader import ModelLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test SARIMAX weekly forecast."""
    logger.info("Testing SARIMAX Weekly Forecast")
    logger.info("=" * 60)
    
    try:
        # Load models (skip transformer to reduce output)
        logger.info("\n1. Loading SARIMAX model...")
        import joblib
        sarimax = joblib.load('artifacts/sarimax_daily.pkl')
        logger.info("✓ SARIMAX model loaded")
        
        # Generate 7-day forecast with exog
        logger.info("\n2. Generating 7-day forecast...")
        
        # SARIMAX needs exog variables (weather features)
        import numpy as np
        # Model expects 3 exog variables: temp, solar, humidity
        exog_forecast = np.array([
            [25.0, 100.0, 60.0]  # temp, solar, humidity
            for _ in range(7)
        ])
        
        forecast = sarimax.forecast(steps=7, exog=exog_forecast)
        
        logger.info(f"✓ Forecast generated: {len(forecast)} days")
        
        # Display results
        logger.info("\n3. Forecast Results:")
        start_date = datetime.utcnow().date() + timedelta(days=1)
        
        for i, value in enumerate(forecast):
            date = start_date + timedelta(days=i)
            logger.info(f"  {date.strftime('%Y-%m-%d')}: {value:.2f} MW (avg)")
        
        # Summary stats
        logger.info("\n4. Summary:")
        logger.info(f"  Weekly average: {forecast.mean():.2f} MW")
        logger.info(f"  Peak day: {forecast.max():.2f} MW")
        logger.info(f"  Min day: {forecast.min():.2f} MW")
        logger.info(f"  Total energy: {forecast.sum() * 24:.2f} MWh")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ SARIMAX TEST PASSED")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
