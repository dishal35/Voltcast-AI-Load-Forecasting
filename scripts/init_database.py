"""
Initialize database schema and verify setup.
Run this before seeding data.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.storage import get_storage_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database schema."""
    logger.info("Initializing database schema...")
    
    try:
        storage = get_storage_service()
        logger.info("✓ Database initialized successfully")
        
        # Check tables
        row_count = storage.get_row_count()
        logger.info(f"✓ hourly_actuals table exists ({row_count} rows)")
        
        if row_count > 0:
            latest_ts = storage.get_latest_timestamp()
            logger.info(f"  Latest timestamp: {latest_ts}")
        else:
            logger.info("  Table is empty - ready for seeding")
        
        logger.info("")
        logger.info("Next step: Run seed script")
        logger.info("  python scripts/seed_hourly_actuals.py hourly_data(2000-2023).csv")
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
