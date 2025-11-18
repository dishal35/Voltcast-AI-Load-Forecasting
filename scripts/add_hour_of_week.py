"""
Add hour_of_week column to master_db.csv and 2025_master_db.csv
hour_of_week = dow * 24 + hour
"""
import pandas as pd

def add_hour_of_week(csv_path):
    """Add hour_of_week column to CSV file."""
    print(f"\nProcessing: {csv_path}")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"  Original columns: {list(df.columns)}")
    print(f"  Original shape: {df.shape}")
    
    # Check if hour_of_week already exists
    if 'hour_of_week' in df.columns:
        print(f"  [SKIP] hour_of_week already exists")
        return
    
    # Calculate hour_of_week
    df['hour_of_week'] = df['dow'] * 24 + df['hour']
    
    # Reorder columns to match model expectations
    # Model expects: temperature_2m, relativehumidity_2m, apparent_temperature, 
    # shortwave_radiation, precipitation, wind_speed_10m, is_holiday, is_weekend, 
    # month, hour_of_week, heat_index, lag_1, lag_24, lag_168, roll24, roll168
    
    # Keep timestamp and load at the beginning
    cols = ['timestamp', 'load']
    
    # Add feature columns in order
    feature_cols = [
        'temperature_2m', 'relativehumidity_2m', 'apparent_temperature',
        'shortwave_radiation', 'precipitation', 'wind_speed_10m',
        'is_holiday', 'is_weekend', 'month', 'hour_of_week', 'heat_index',
        'lag_1', 'lag_24', 'lag_168', 'roll24', 'roll168'
    ]
    
    # Add any remaining columns (dow, hour for reference)
    remaining = [c for c in df.columns if c not in cols + feature_cols]
    
    final_cols = cols + feature_cols + remaining
    df = df[final_cols]
    
    # Save back
    df.to_csv(csv_path, index=False)
    print(f"  [SUCCESS] Added hour_of_week column")
    print(f"  New columns: {list(df.columns)}")
    print(f"  New shape: {df.shape}")
    print(f"  Sample hour_of_week values: {df['hour_of_week'].head().tolist()}")
    print(f"  Min: {df['hour_of_week'].min()}, Max: {df['hour_of_week'].max()}")

if __name__ == "__main__":
    print("="*60)
    print("Adding hour_of_week column to CSV files")
    print("="*60)
    
    # Process both files
    add_hour_of_week('scripts/master_db.csv')
    add_hour_of_week('scripts/2025_master_db.csv')
    
    print("\n" + "="*60)
    print("[SUCCESS] All files updated")
    print("="*60)
