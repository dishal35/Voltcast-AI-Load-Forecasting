"""
Validate 2025 Dataset - Check for Missing Values and Data Quality
"""

import pandas as pd
import numpy as np

print("="*80)
print("VALIDATING 2025 DATASET")
print("="*80)

# Load the dataset
df = pd.read_csv('scripts/master_db_2025.csv', parse_dates=['timestamp'])
df = df.set_index('timestamp').sort_index()

print(f"\n📊 Dataset Overview:")
print(f"  Total records: {len(df):,}")
print(f"  Date range: {df.index.min()} → {df.index.max()}")
print(f"  Columns: {len(df.columns)}")

# ============================================================
# CHECK MISSING VALUES
# ============================================================
print("\n" + "="*80)
print("MISSING VALUES ANALYSIS")
print("="*80)

missing_summary = []
for col in df.columns:
    missing_count = df[col].isna().sum()
    missing_pct = (missing_count / len(df)) * 100
    missing_summary.append({
        'Column': col,
        'Missing': missing_count,
        'Percentage': missing_pct
    })

missing_df = pd.DataFrame(missing_summary).sort_values('Missing', ascending=False)

print("\nMissing Values by Column:")
print("-" * 60)
for _, row in missing_df.iterrows():
    status = "✓" if row['Missing'] == 0 else "⚠" if row['Percentage'] < 5 else "✗"
    print(f"{status} {row['Column']:25s}: {row['Missing']:5,} ({row['Percentage']:5.2f}%)")

# ============================================================
# WEATHER DATA VALIDATION
# ============================================================
print("\n" + "="*80)
print("WEATHER DATA VALIDATION")
print("="*80)

weather_cols = ['temperature_2m', 'relativehumidity_2m', 'apparent_temperature',
                'shortwave_radiation', 'precipitation', 'wind_speed_10m', 'heat_index']

weather_complete = True
for col in weather_cols:
    missing = df[col].isna().sum()
    if missing > 0:
        print(f"✗ {col}: {missing} missing values")
        weather_complete = False
    else:
        print(f"✓ {col}: Complete (no missing values)")

if weather_complete:
    print("\n✅ All weather data is complete!")
else:
    print("\n⚠ Some weather data is missing - needs attention")

# ============================================================
# LOAD DATA VALIDATION
# ============================================================
print("\n" + "="*80)
print("LOAD DATA VALIDATION")
print("="*80)

load_missing = df['load'].isna().sum()
load_coverage = (df['load'].notna().sum() / len(df)) * 100

print(f"\nLoad Data Coverage:")
print(f"  Total hours: {len(df):,}")
print(f"  Hours with data: {df['load'].notna().sum():,}")
print(f"  Missing hours: {load_missing:,}")
print(f"  Coverage: {load_coverage:.2f}%")

if load_coverage >= 95:
    print(f"  ✅ Excellent coverage (≥95%)")
elif load_coverage >= 90:
    print(f"  ✓ Good coverage (≥90%)")
elif load_coverage >= 80:
    print(f"  ⚠ Acceptable coverage (≥80%)")
else:
    print(f"  ✗ Poor coverage (<80%)")

# Check for consecutive missing hours
if load_missing > 0:
    print("\n  Analyzing missing load data patterns...")
    missing_mask = df['load'].isna()
    
    # Find consecutive missing periods
    missing_groups = (missing_mask != missing_mask.shift()).cumsum()
    missing_periods = df[missing_mask].groupby(missing_groups).size()
    
    if len(missing_periods) > 0:
        print(f"  Number of missing periods: {len(missing_periods)}")
        print(f"  Longest missing period: {missing_periods.max()} hours")
        print(f"  Average missing period: {missing_periods.mean():.1f} hours")
        
        # Show largest gaps
        if missing_periods.max() > 24:
            print("\n  ⚠ Large gaps detected (>24 hours):")
            large_gaps = missing_periods[missing_periods > 24].sort_values(ascending=False).head(5)
            for idx, gap_size in large_gaps.items():
                gap_start = df[missing_mask & (missing_groups == idx)].index.min()
                gap_end = df[missing_mask & (missing_groups == idx)].index.max()
                print(f"    {gap_start} → {gap_end}: {gap_size} hours")

# ============================================================
# LAG FEATURES VALIDATION
# ============================================================
print("\n" + "="*80)
print("LAG FEATURES VALIDATION")
print("="*80)

lag_cols = ['lag_1', 'lag_24', 'lag_168', 'roll24', 'roll168']

print("\nLag Feature Completeness:")
for col in lag_cols:
    if col in df.columns:
        non_null = df[col].notna().sum()
        pct = (non_null / len(df)) * 100
        print(f"  {col:10s}: {non_null:5,} / {len(df):,} ({pct:5.1f}%)")
    else:
        print(f"  {col:10s}: Column not found")

# Expected missing for lag features at the start
expected_missing_lag1 = 1
expected_missing_lag24 = 24
expected_missing_lag168 = 168

actual_missing_lag1 = df['lag_1'].isna().sum()
actual_missing_lag24 = df['lag_24'].isna().sum()
actual_missing_lag168 = df['lag_168'].isna().sum()

print(f"\nLag Feature Validation:")
if actual_missing_lag1 <= expected_missing_lag1 + load_missing:
    print(f"  ✓ lag_1 missing count is expected")
else:
    print(f"  ⚠ lag_1 has more missing values than expected")

if actual_missing_lag24 <= expected_missing_lag24 + load_missing:
    print(f"  ✓ lag_24 missing count is expected")
else:
    print(f"  ⚠ lag_24 has more missing values than expected")

if actual_missing_lag168 <= expected_missing_lag168 + load_missing:
    print(f"  ✓ lag_168 missing count is expected")
else:
    print(f"  ⚠ lag_168 has more missing values than expected")

# ============================================================
# DATA QUALITY CHECKS
# ============================================================
print("\n" + "="*80)
print("DATA QUALITY CHECKS")
print("="*80)

quality_issues = []

# Check for negative values in load
if (df['load'] < 0).any():
    neg_count = (df['load'] < 0).sum()
    quality_issues.append(f"Negative load values: {neg_count}")
    print(f"✗ Found {neg_count} negative load values")
else:
    print(f"✓ No negative load values")

# Check for unrealistic load values (e.g., > 10,000 MW for Delhi)
if (df['load'] > 10000).any():
    high_count = (df['load'] > 10000).sum()
    quality_issues.append(f"Unrealistically high load values: {high_count}")
    print(f"✗ Found {high_count} unrealistically high load values (>10,000 MW)")
else:
    print(f"✓ No unrealistically high load values")

# Check temperature range
temp_min = df['temperature_2m'].min()
temp_max = df['temperature_2m'].max()
if temp_min < -10 or temp_max > 50:
    quality_issues.append(f"Temperature out of expected range: {temp_min:.1f}°C to {temp_max:.1f}°C")
    print(f"⚠ Temperature range seems unusual: {temp_min:.1f}°C to {temp_max:.1f}°C")
else:
    print(f"✓ Temperature range is reasonable: {temp_min:.1f}°C to {temp_max:.1f}°C")

# Check humidity range
rh_min = df['relativehumidity_2m'].min()
rh_max = df['relativehumidity_2m'].max()
if rh_min < 0 or rh_max > 100:
    quality_issues.append(f"Humidity out of valid range: {rh_min:.1f}% to {rh_max:.1f}%")
    print(f"✗ Humidity out of valid range: {rh_min:.1f}% to {rh_max:.1f}%")
else:
    print(f"✓ Humidity range is valid: {rh_min:.1f}% to {rh_max:.1f}%")

# Check for duplicate timestamps
duplicates = df.index.duplicated().sum()
if duplicates > 0:
    quality_issues.append(f"Duplicate timestamps: {duplicates}")
    print(f"✗ Found {duplicates} duplicate timestamps")
else:
    print(f"✓ No duplicate timestamps")

# Check for time gaps
expected_freq = pd.Timedelta('1h')
time_diffs = df.index.to_series().diff()
gaps = (time_diffs > expected_freq).sum()
if gaps > 0:
    quality_issues.append(f"Time gaps detected: {gaps}")
    print(f"⚠ Found {gaps} time gaps (>1 hour)")
else:
    print(f"✓ No time gaps detected")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

if len(quality_issues) == 0 and weather_complete and load_coverage >= 95:
    print("\n✅ DATASET VALIDATION PASSED!")
    print("   All checks passed. Dataset is ready for modeling.")
elif len(quality_issues) == 0 and weather_complete:
    print("\n✓ DATASET VALIDATION MOSTLY PASSED")
    print(f"   Weather data is complete, load coverage is {load_coverage:.1f}%")
    print("   Dataset is usable for modeling.")
else:
    print("\n⚠ DATASET VALIDATION COMPLETED WITH WARNINGS")
    print(f"   Found {len(quality_issues)} quality issues:")
    for issue in quality_issues:
        print(f"   - {issue}")
    if not weather_complete:
        print("   - Weather data has missing values")
    print("\n   Review issues before proceeding with modeling.")

# ============================================================
# RECOMMENDATIONS
# ============================================================
print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

if load_missing > 0:
    print("\n📝 For missing load data:")
    if load_missing < len(df) * 0.05:  # Less than 5%
        print("   • Small gaps can be filled with hour-of-week median")
        print("   • Or use model predictions to fill gaps")
    else:
        print("   • Consider re-scraping missing dates from SLDC website")
        print("   • Or use model predictions for missing hours")

if not weather_complete:
    print("\n📝 For missing weather data:")
    print("   • Forward-fill or backward-fill weather values")
    print("   • Weather data typically doesn't have large gaps")

if df['roll168'].isna().sum() > 168:
    print("\n📝 For rolling features:")
    print("   • First 168 hours will naturally have NaN for roll168")
    print("   • This is expected and acceptable")

print("\n" + "="*80)
