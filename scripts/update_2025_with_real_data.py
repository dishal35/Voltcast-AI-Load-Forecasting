"""
Update 2025 Master DB with Real SLDC Data
Fetches actual data from SLDC website and replaces synthetic data in CSV.
"""
import sys
sys.path.insert(0, '.')

from api.services.data_sync import sync_2025_data
import pandas as pd
from datetime import datetime

print("=" * 80)
print("UPDATING 2025 MASTER DB WITH REAL SLDC DATA")
print("=" * 80)

# Check current CSV
try:
    df = pd.read_csv('scripts/2025_master_db.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"\nCurrent CSV:")
    print(f"  Records: {len(df)}")
    print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"  First load value: {df['load'].iloc[0]:.2f} MW")
except FileNotFoundError:
    print("\n2025_master_db.csv not found")
    df = None

# Sync real data from SLDC
print(f"\nFetching real data from SLDC website...")
print("This will:")
print("  1. Scrape actual load data from http://www.delhisldc.org")
print("  2. Fetch real weather data from Open-Meteo")
print("  3. Compute proper features with 2024 history")
print("  4. Replace synthetic data with real data")

response = input("\nProceed? (y/n): ").strip().lower()

if response == 'y':
    print("\nSyncing data...")
    success, message = sync_2025_data(force_update=True)
    
    if success:
        print(f"\n✓ {message}")
        
        # Check updated CSV
        df_new = pd.read_csv('scripts/2025_master_db.csv')
        df_new['timestamp'] = pd.to_datetime(df_new['timestamp'])
        
        print(f"\nUpdated CSV:")
        print(f"  Records: {len(df_new)}")
        print(f"  Date range: {df_new['timestamp'].min()} → {df_new['timestamp'].max()}")
        print(f"  First load value: {df_new['load'].iloc[0]:.2f} MW")
        
        # Show sample of recent data
        print(f"\nLast 5 records:")
        print(df_new[['timestamp', 'load']].tail())
        
        print("\n" + "=" * 80)
        print("✓ UPDATE COMPLETE")
        print("=" * 80)
        print("\nThe CSV now contains REAL data from SLDC website.")
        print("You can verify by comparing with: http://www.delhisldc.org/Loaddata.aspx")
    else:
        print(f"\n✗ {message}")
else:
    print("\nCancelled.")
