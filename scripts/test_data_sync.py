"""
Test Data Synchronization
Tests the data sync service that fetches SLDC and weather data.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.services.data_sync import (
    sync_2025_data,
    get_actual_load,
    get_actual_loads_range,
    scrape_sldc_day,
    fetch_weather_range
)
from datetime import datetime, date, timedelta
import pandas as pd


def test_scrape_sldc():
    """Test SLDC scraping for a single day."""
    print("=" * 80)
    print("TEST 1: SLDC Scraping")
    print("=" * 80)
    
    # Test with a known date in 2025
    test_date = date(2025, 1, 15)
    
    print(f"\nScraping SLDC data for {test_date}...")
    df = scrape_sldc_day(test_date)
    
    if not df.empty:
        print(f"✓ Scraped {len(df)} records")
        print(f"\nFirst 5 records:")
        print(df.head())
        print(f"\nLoad statistics:")
        print(f"  Mean: {df['load'].mean():.2f} MW")
        print(f"  Min: {df['load'].min():.2f} MW")
        print(f"  Max: {df['load'].max():.2f} MW")
    else:
        print("✗ No data scraped (may be unavailable or network issue)")


def test_fetch_weather():
    """Test weather data fetching."""
    print("\n" + "=" * 80)
    print("TEST 2: Weather Data Fetching")
    print("=" * 80)
    
    start_date = "2025-01-01"
    end_date = "2025-01-07"
    
    print(f"\nFetching weather data from {start_date} to {end_date}...")
    df = fetch_weather_range(start_date, end_date)
    
    if not df.empty:
        print(f"✓ Fetched {len(df)} hourly records")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst 5 records:")
        print(df.head())
        print(f"\nTemperature statistics:")
        print(f"  Mean: {df['temperature_2m'].mean():.2f} °C")
        print(f"  Min: {df['temperature_2m'].min():.2f} °C")
        print(f"  Max: {df['temperature_2m'].max():.2f} °C")
    else:
        print("✗ No weather data fetched")


def test_sync_2025_data():
    """Test full data synchronization."""
    print("\n" + "=" * 80)
    print("TEST 3: Full Data Synchronization")
    print("=" * 80)
    
    print("\nSyncing 2025 data (this may take a few minutes)...")
    success, message = sync_2025_data(force_update=False)
    
    if success:
        print(f"✓ {message}")
        
        # Verify CSV was updated
        if os.path.exists('scripts/2025_master_db.csv'):
            df = pd.read_csv('scripts/2025_master_db.csv', parse_dates=['timestamp'])
            print(f"\n2025 Master DB:")
            print(f"  Total records: {len(df)}")
            print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
            print(f"  Columns: {len(df.columns)}")
            
            # Check completeness
            print(f"\nData completeness:")
            for col in ['load', 'temperature_2m', 'lag_1', 'lag_24', 'lag_168']:
                non_null = df[col].notna().sum()
                pct = (non_null / len(df)) * 100
                print(f"  {col:20s}: {non_null:5,} / {len(df):,} ({pct:5.1f}%)")
        else:
            print("✗ 2025_master_db.csv not found")
    else:
        print(f"✗ {message}")


def test_get_actual_load():
    """Test getting actual load for specific timestamps."""
    print("\n" + "=" * 80)
    print("TEST 4: Get Actual Load Values")
    print("=" * 80)
    
    # Test with 2024 data (should exist)
    test_timestamps = [
        datetime(2024, 1, 1, 12, 0, 0),
        datetime(2024, 6, 15, 18, 0, 0),
        datetime(2025, 1, 15, 10, 0, 0),  # May or may not exist
    ]
    
    print("\nGetting actual load values:")
    for ts in test_timestamps:
        load = get_actual_load(ts)
        if load is not None:
            print(f"  {ts}: {load:.2f} MW ✓")
        else:
            print(f"  {ts}: Not available ✗")


def test_get_actual_loads_range():
    """Test getting actual loads for a time range."""
    print("\n" + "=" * 80)
    print("TEST 5: Get Actual Loads Range")
    print("=" * 80)
    
    # Test with 2024 data
    start_ts = datetime(2024, 1, 1, 0, 0, 0)
    end_ts = datetime(2024, 1, 1, 23, 0, 0)
    
    print(f"\nGetting actual loads from {start_ts} to {end_ts}...")
    df = get_actual_loads_range(start_ts, end_ts)
    
    if not df.empty:
        print(f"✓ Retrieved {len(df)} hourly records")
        print(f"\nFirst 5 records:")
        print(df.head())
        print(f"\nLoad statistics:")
        print(f"  Mean: {df['load'].mean():.2f} MW")
        print(f"  Min: {df['load'].min():.2f} MW")
        print(f"  Max: {df['load'].max():.2f} MW")
    else:
        print("✗ No data retrieved")


def test_prediction_with_actuals():
    """Test prediction API with actual values."""
    print("\n" + "=" * 80)
    print("TEST 6: Prediction with Actuals")
    print("=" * 80)
    
    import requests
    
    url = "http://localhost:8000/api/v1/predict/horizon"
    payload = {
        "timestamp": "2024-01-01T00:00:00",
        "horizon": 24
    }
    
    try:
        print("\nCalling prediction API...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        predictions = data['predictions']
        actuals = data.get('actuals', [])
        
        print(f"✓ Received {len(predictions)} predictions")
        print(f"  Actuals available: {sum(1 for a in actuals if a is not None)}/{len(actuals)}")
        
        # Show first 5 with actuals
        print(f"\n{'Hour':<6} {'Predicted':<12} {'Actual':<12} {'Error':<10}")
        print("-" * 46)
        for i in range(min(5, len(predictions))):
            pred = predictions[i]
            actual = actuals[i] if i < len(actuals) else None
            if actual is not None:
                error = pred - actual
                print(f"{i:<6} {pred:<12.2f} {actual:<12.2f} {error:<10.2f}")
            else:
                print(f"{i:<6} {pred:<12.2f} {'N/A':<12} {'N/A':<10}")
        
        # Calculate MAE for available actuals
        errors = []
        for i in range(len(predictions)):
            if i < len(actuals) and actuals[i] is not None:
                errors.append(abs(predictions[i] - actuals[i]))
        
        if errors:
            mae = sum(errors) / len(errors)
            print(f"\nMAE (for available actuals): {mae:.2f} MW")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ API not running. Start with: python run_api.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("DATA SYNCHRONIZATION TEST SUITE")
    print("=" * 80)
    
    # Run tests
    test_scrape_sldc()
    test_fetch_weather()
    test_sync_2025_data()
    test_get_actual_load()
    test_get_actual_loads_range()
    test_prediction_with_actuals()
    
    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETE")
    print("=" * 80)
