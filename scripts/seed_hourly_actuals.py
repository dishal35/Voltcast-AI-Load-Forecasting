"""
Seed historical data from CSV into the database.
Loads hourly_data(2000-2023).csv into hourly_actuals table.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from api.services.storage import get_storage_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load and prepare CSV data for database insertion."""
    logger.info(f"Loading CSV from {csv_path}")
    
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} rows from CSV")
    
    # Rename columns to match database schema
    column_mapping = {
        'Datetime': 'ts',
        'timestamp': 'ts',  # Alternative name
        'Delhi_demand': 'demand',
        'electricity_demand': 'demand',  # Alternative name
        'Delhi_temp': 'temperature',
        'Delhi_humidity': 'humidity',
        'Delhi_wind_speed': 'wind_speed',
        'Delhi_solar_generation': 'solar_generation',
        'solar_generation': 'solar_generation',  # Already correct
        'Delhi_cloud_cover': 'cloud_cover',
        'Delhi_is_holiday': 'is_holiday',
        'is_holiday': 'is_holiday'  # Already correct
    }
    
    # Check which columns exist and rename
    existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=existing_mapping)
    
    # Ensure required columns exist
    if 'ts' not in df.columns:
        raise ValueError("CSV must contain 'Datetime' or 'timestamp' column")
    if 'demand' not in df.columns:
        raise ValueError("CSV must contain 'Delhi_demand' or 'electricity_demand' column")
    
    # Convert timestamp
    df['ts'] = pd.to_datetime(df['ts'])
    
    # Handle missing columns
    for col in ['temperature', 'humidity', 'wind_speed', 
                'solar_generation', 'cloud_cover']:
        if col not in df.columns:
            logger.warning(f"Column {col} not found in CSV, will be set to NULL")
            df[col] = None
    
    if 'is_holiday' not in df.columns:
        df['is_holiday'] = False
    
    # Select only relevant columns
    columns = ['ts', 'demand', 'temperature', 'humidity', 'wind_speed',
               'solar_generation', 'cloud_cover', 'is_holiday']
    df = df[columns]
    
    # Remove duplicates and sort
    df = df.drop_duplicates(subset=['ts']).sort_values('ts')
    
    logger.info(f"Prepared {len(df)} unique records for insertion")
    logger.info(f"Date range: {df['ts'].min()} to {df['ts'].max()}")
    
    return df


def seed_database(csv_path: str, batch_size: int = 1000):
    """
    Seed the database with historical data.
    
    Args:
        csv_path: Path to CSV file
        batch_size: Number of rows to insert per batch
    """
    # Load data
    df = load_csv_data(csv_path)
    
    # Get storage service
    storage = get_storage_service()
    
    # Check existing data
    existing_count = storage.get_row_count()
    logger.info(f"Database currently has {existing_count} rows")
    
    if existing_count > 0:
        latest_ts = storage.get_latest_timestamp()
        logger.info(f"Latest timestamp in DB: {latest_ts}")
        
        response = input("Database already contains data. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Seeding cancelled")
            return
    
    # Insert in batches
    total_rows = len(df)
    inserted = 0
    
    for i in range(0, total_rows, batch_size):
        batch = df.iloc[i:i+batch_size]
        storage.append_actuals(batch)
        inserted += len(batch)
        logger.info(f"Progress: {inserted}/{total_rows} rows ({100*inserted/total_rows:.1f}%)")
    
    # Verify
    final_count = storage.get_row_count()
    latest_ts = storage.get_latest_timestamp()
    
    logger.info("=" * 60)
    logger.info("Seeding complete!")
    logger.info(f"Total rows in database: {final_count}")
    logger.info(f"Latest timestamp: {latest_ts}")
    logger.info("=" * 60)


def main():
    """Main entry point."""
    # Find CSV file
    possible_paths = [
        'hourly_data(2000-2023).csv',
        'data/hourly_data(2000-2023).csv',
        '../hourly_data(2000-2023).csv',
    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if csv_path is None:
        logger.error("Could not find hourly_data(2000-2023).csv")
        logger.error("Please provide path as argument: python seed_hourly_actuals.py <path>")
        
        if len(sys.argv) > 1:
            csv_path = sys.argv[1]
            if not os.path.exists(csv_path):
                logger.error(f"File not found: {csv_path}")
                sys.exit(1)
        else:
            sys.exit(1)
    
    logger.info(f"Using CSV file: {csv_path}")
    seed_database(csv_path)


if __name__ == '__main__':
    main()
