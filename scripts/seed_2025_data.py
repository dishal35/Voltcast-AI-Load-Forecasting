"""
Seed database with 2025 data from 2025_master_db.csv
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from datetime import datetime
from api.services.storage import get_storage_service

def main():
    print("="*60)
    print("Seeding Database with 2025 Data")
    print("="*60)
    
    # Load CSV
    print("\n1. Loading 2025_master_db.csv...")
    df = pd.read_csv('scripts/2025_master_db.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"   Loaded {len(df)} rows")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Initialize storage
    print("\n2. Initializing database...")
    storage = get_storage_service()
    print("   Database initialized")
    
    # Insert data using SQL
    print("\n3. Inserting data into database...")
    from sqlalchemy import text
    
    inserted = 0
    skipped = 0
    
    with storage.engine.connect() as conn:
        for idx, row in df.iterrows():
            try:
                conn.execute(text("""
                    INSERT OR REPLACE INTO hourly_actuals 
                    (ts, demand, temperature, humidity, wind_speed, solar_generation, cloud_cover, is_holiday)
                    VALUES (:ts, :demand, :temperature, :humidity, :wind_speed, :solar, :cloud, :holiday)
                """), {
                    'ts': str(row['timestamp']),
                    'demand': float(row['load']),
                    'temperature': float(row.get('temperature_2m', 25.0)),
                    'humidity': float(row.get('relativehumidity_2m', 60.0)),
                    'wind_speed': float(row.get('wind_speed_10m', 3.5)),
                    'solar': float(row.get('shortwave_radiation', 50.0)),
                    'cloud': 40.0,  # Not in CSV
                    'holiday': int(row.get('is_holiday', 0))
                })
                inserted += 1
                
                if (idx + 1) % 1000 == 0:
                    print(f"   Inserted {idx + 1}/{len(df)} rows...")
                    conn.commit()
                    
            except Exception as e:
                skipped += 1
                if skipped < 5:  # Only print first few errors
                    print(f"   Skipped row {idx}: {e}")
        
        conn.commit()
    
    print(f"\n4. Complete!")
    print(f"   Inserted: {inserted} rows")
    print(f"   Skipped:  {skipped} rows")
    
    # Verify
    print("\n5. Verifying data...")
    test_date = datetime(2025, 1, 8, 0, 0)
    data = storage.get_range(test_date, datetime(2025, 1, 8, 10, 0))
    print(f"   Found {len(data)} rows for 2025-01-08 00:00 to 10:00")
    
    if len(data) > 0:
        print(f"   Sample data:")
        print(data.head())
        print("\n   [SUCCESS] Database seeded with 2025 data")
        return True
    else:
        print("\n   [FAILED] No data found after seeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
