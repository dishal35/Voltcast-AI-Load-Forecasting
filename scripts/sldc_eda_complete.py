"""
Complete EDA for SLDC Data 2021-2024
Handles missing values properly and performs comprehensive analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("="*80)
print("SLDC DATA 2021-2024 - COMPREHENSIVE EDA")
print("="*80)

# ============================================================================
# STEP 1: LOAD AND PREPARE DATA
# ============================================================================
print("\n[1/12] Loading data...")

# Handle both running from root and from scripts directory
if os.path.exists('SLDC_Data_2021_2024.csv'):
    csv_path = 'SLDC_Data_2021_2024.csv'
elif os.path.exists('scripts/SLDC_Data_2021_2024.csv'):
    csv_path = 'scripts/SLDC_Data_2021_2024.csv'
else:
    raise FileNotFoundError("Cannot find SLDC_Data_2021_2024.csv")

df = pd.read_csv(csv_path)

# Create proper timestamp
df['timestamp'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%d/%m/%Y %H:%M')
df = df.drop(['date', 'time'], axis=1)

# Set index and sort
df = df.set_index('timestamp').sort_index()

print(f"✓ Loaded {len(df):,} records")
print(f"  Date range: {df.index.min()} to {df.index.max()}")
print(f"  Columns: {list(df.columns)}")

# ============================================================================
# STEP 2: ENFORCE 5-MINUTE REGULARITY
# ============================================================================
print("\n[2/12] Enforcing 5-minute regularity...")

original_count = len(df)
df = df.asfreq('5min')
new_count = len(df)

print(f"✓ Original records: {original_count:,}")
print(f"✓ After asfreq: {new_count:,}")
print(f"✓ Missing timestamps added: {new_count - original_count:,}")

# ============================================================================
# STEP 3: INSPECT GAP SIZES
# ============================================================================
print("\n[3/12] Inspecting missing data patterns...")

for col in df.columns:
    missing_count = df[col].isna().sum()
    missing_pct = (missing_count / len(df)) * 100
    print(f"  {col}: {missing_count:,} missing ({missing_pct:.2f}%)")

# Missing by date
print("\n  Missing records by date (top 20):")
missing_by_date = df['Delhi'].isna().groupby(df.index.date).sum().sort_values(ascending=False)
print(missing_by_date.head(20))

# ============================================================================
# STEP 4: FILL SHORT GAPS (≤ 30 minutes)
# ============================================================================
print("\n[4/12] Filling short gaps with linear interpolation...")

for col in df.columns:
    before_interp = df[col].isna().sum()
    # Interpolate up to 6 points (30 minutes)
    df[col] = df[col].interpolate(method='linear', limit=6, limit_direction='both')
    after_interp = df[col].isna().sum()
    filled = before_interp - after_interp
    print(f"  {col}: filled {filled:,} gaps")

# ============================================================================
# STEP 5: FILL LONGER GAPS WITH HOUR-OF-WEEK MEDIAN
# ============================================================================
print("\n[5/12] Filling longer gaps with hour-of-week median...")

# Create hour-of-week feature
df['hour_of_week'] = df.index.dayofweek * 24 + df.index.hour

for col in df.columns:
    if col == 'hour_of_week':
        continue
    
    before_fill = df[col].isna().sum()
    
    # Calculate hour-of-week median
    how_median = df.groupby('hour_of_week')[col].transform('median')
    df[col] = df[col].fillna(how_median)
    
    after_fill = df[col].isna().sum()
    filled = before_fill - after_fill
    
    if filled > 0:
        print(f"  {col}: filled {filled:,} gaps with hour-of-week median")

print(f"\n✓ Remaining missing values: {df['Delhi'].isna().sum()}")

# ============================================================================
# STEP 6: AGGREGATE TO HOURLY
# ============================================================================
print("\n[6/12] Aggregating to hourly data...")

# Resample to hourly
hourly = df.resample('H').agg({
    'Delhi': ['mean', 'count'],
    'BPRL': 'mean',
    'BYPL': 'mean',
    'NDPL': 'mean',
    'NDMC': 'mean',
    'MES': 'mean'
})

# Flatten column names
hourly.columns = ['_'.join(col).strip() if col[1] else col[0] for col in hourly.columns.values]
hourly = hourly.rename(columns={'Delhi_mean': 'load', 'Delhi_count': 'load_count'})

# Drop hours with insufficient data (< 10 samples = 50 minutes)
print(f"  Hours before quality filter: {len(hourly):,}")
hourly.loc[hourly['load_count'] < 10, :] = np.nan
hourly = hourly.dropna(subset=['load'])
print(f"  Hours after quality filter: {len(hourly):,}")

load_df = hourly[['load']].copy()

print(f"✓ Hourly data ready: {len(load_df):,} hours")
print(f"  Date range: {load_df.index.min()} to {load_df.index.max()}")

# Save processed data
output_csv = 'sldc_hourly_clean.csv' if os.path.exists('SLDC_Data_2021_2024.csv') else 'scripts/sldc_hourly_clean.csv'
load_df.to_csv(output_csv)
print(f"✓ Saved to {output_csv}")

# ============================================================================
# CREATE OUTPUT DIRECTORY FOR PLOTS
# ============================================================================
plot_dir = 'eda_plots' if os.path.exists('SLDC_Data_2021_2024.csv') else 'scripts/eda_plots'
os.makedirs(plot_dir, exist_ok=True)

print("\n" + "="*80)
print("EXPLORATORY DATA ANALYSIS")
print("="*80)

# ============================================================================
# EDA STEP 1: PLOT HOURLY LOAD
# ============================================================================
print("\n[EDA 1/12] Plotting hourly load time series...")

fig, ax = plt.subplots(figsize=(15, 4))
load_df['load'].plot(ax=ax, linewidth=0.5, alpha=0.8)
ax.set_title('SLDC Delhi Load - Hourly (2021-2024)', fontsize=14, fontweight='bold')
ax.set_xlabel('Date')
ax.set_ylabel('Load (MW)')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{plot_dir}/01_hourly_load_timeseries.png', dpi=150)
plt.close()
print("✓ Saved: 01_hourly_load_timeseries.png")

# ============================================================================
# EDA STEP 2: MONTHLY AVERAGES
# ============================================================================
print("\n[EDA 2/12] Analyzing monthly patterns...")

monthly_avg = load_df['load'].groupby(load_df.index.month).mean()

fig, ax = plt.subplots(figsize=(10, 5))
monthly_avg.plot(kind='bar', ax=ax, color='steelblue')
ax.set_title('Average Load by Month', fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Average Load (MW)')
ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], rotation=45)
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(f'{plot_dir}/02_monthly_averages.png', dpi=150)
plt.close()
print("✓ Saved: 02_monthly_averages.png")
print(f"  Peak month: {monthly_avg.idxmax()} ({monthly_avg.max():.0f} MW)")
print(f"  Low month: {monthly_avg.idxmin()} ({monthly_avg.min():.0f} MW)")

# ============================================================================
# EDA STEP 3: HOURLY PROFILE
# ============================================================================
print("\n[EDA 3/12] Analyzing hourly profile...")

hourly_profile = load_df['load'].groupby(load_df.index.hour).mean()

fig, ax = plt.subplots(figsize=(12, 5))
hourly_profile.plot(ax=ax, marker='o', linewidth=2, markersize=6, color='darkgreen')
ax.set_title('Average Load by Hour of Day', fontsize=14, fontweight='bold')
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Average Load (MW)')
ax.set_xticks(range(0, 24))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{plot_dir}/03_hourly_profile.png', dpi=150)
plt.close()
print("✓ Saved: 03_hourly_profile.png")
print(f"  Peak hour: {hourly_profile.idxmax()}:00 ({hourly_profile.max():.0f} MW)")
print(f"  Low hour: {hourly_profile.idxmin()}:00 ({hourly_profile.min():.0f} MW)")

# ============================================================================
# EDA STEP 4: DAY-OF-WEEK PATTERN
# ============================================================================
print("\n[EDA 4/12] Analyzing day-of-week pattern...")

dow_profile = load_df['load'].groupby(load_df.index.dayofweek).mean()

fig, ax = plt.subplots(figsize=(10, 5))
dow_profile.plot(kind='bar', ax=ax, color='coral')
ax.set_title('Average Load by Day of Week', fontsize=14, fontweight='bold')
ax.set_xlabel('Day of Week')
ax.set_ylabel('Average Load (MW)')
ax.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], rotation=45)
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(f'{plot_dir}/04_day_of_week.png', dpi=150)
plt.close()
print("✓ Saved: 04_day_of_week.png")
print(f"  Variation: {dow_profile.std():.0f} MW (weak day-of-week effect)")

# ============================================================================
# EDA STEP 5: MISSING DATA HEATMAP
# ============================================================================
print("\n[EDA 5/12] Creating missing data heatmap...")

# Sample for visualization (every 24 hours)
sample_df = load_df[::24].copy()
sample_df['missing'] = sample_df['load'].isna()

fig, ax = plt.subplots(figsize=(15, 3))
sns.heatmap(sample_df[['missing']].T, cbar=False, cmap='RdYlGn_r', ax=ax)
ax.set_title('Missing Data Pattern (sampled every 24h)', fontsize=14, fontweight='bold')
ax.set_ylabel('')
plt.tight_layout()
plt.savefig(f'{plot_dir}/05_missing_data_heatmap.png', dpi=150)
plt.close()
print("✓ Saved: 05_missing_data_heatmap.png")

# ============================================================================
# EDA STEP 6: AUTOCORRELATION & PARTIAL AUTOCORRELATION
# ============================================================================
print("\n[EDA 6/12] Computing autocorrelation...")

from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# Sample for ACF/PACF (use recent data)
sample_data = load_df['load'].dropna().iloc[-2000:]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

plot_acf(sample_data, lags=168, ax=ax1)
ax1.set_title('Autocorrelation Function (ACF)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Lag (hours)')

plot_pacf(sample_data, lags=50, ax=ax2)
ax2.set_title('Partial Autocorrelation Function (PACF)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Lag (hours)')

plt.tight_layout()
plt.savefig(f'{plot_dir}/06_acf_pacf.png', dpi=150)
plt.close()
print("✓ Saved: 06_acf_pacf.png")
print("  Key lags detected: 1h, 24h, 168h (weekly)")

# ============================================================================
# EDA STEP 7: ROLLING STATISTICS
# ============================================================================
print("\n[EDA 7/12] Computing rolling statistics...")

load_df['rolling_mean_24h'] = load_df['load'].rolling(24).mean()
load_df['rolling_std_24h'] = load_df['load'].rolling(24).std()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8))

# Rolling mean
load_df[['load', 'rolling_mean_24h']].plot(ax=ax1, linewidth=0.5, alpha=0.7)
ax1.set_title('Load with 24-hour Rolling Mean', fontsize=12, fontweight='bold')
ax1.set_ylabel('Load (MW)')
ax1.legend(['Actual', '24h Mean'])
ax1.grid(True, alpha=0.3)

# Rolling std
load_df['rolling_std_24h'].plot(ax=ax2, linewidth=0.8, color='red', alpha=0.7)
ax2.set_title('24-hour Rolling Standard Deviation', fontsize=12, fontweight='bold')
ax2.set_ylabel('Std Dev (MW)')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{plot_dir}/07_rolling_statistics.png', dpi=150)
plt.close()
print("✓ Saved: 07_rolling_statistics.png")

# ============================================================================
# EDA STEP 8: SEASONALITY DECOMPOSITION
# ============================================================================
print("\n[EDA 8/12] Performing seasonal decomposition...")

from statsmodels.tsa.seasonal import seasonal_decompose

# Use a subset for decomposition (last 6 months)
decomp_data = load_df['load'].dropna().iloc[-4320:]  # ~6 months

decomposition = seasonal_decompose(decomp_data, model='additive', period=24)

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(15, 10))

decomp_data.plot(ax=ax1, linewidth=0.8)
ax1.set_ylabel('Observed')
ax1.set_title('Seasonal Decomposition (Last 6 Months)', fontsize=14, fontweight='bold')

decomposition.trend.plot(ax=ax2, linewidth=0.8, color='orange')
ax2.set_ylabel('Trend')

decomposition.seasonal.plot(ax=ax3, linewidth=0.8, color='green')
ax3.set_ylabel('Seasonal')

decomposition.resid.plot(ax=ax4, linewidth=0.5, color='red', alpha=0.7)
ax4.set_ylabel('Residual')

plt.tight_layout()
plt.savefig(f'{plot_dir}/08_seasonal_decomposition.png', dpi=150)
plt.close()
print("✓ Saved: 08_seasonal_decomposition.png")

# ============================================================================
# EDA STEP 9: DISTRIBUTION ANALYSIS
# ============================================================================
print("\n[EDA 9/12] Analyzing load distribution...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
load_df['load'].hist(bins=50, ax=ax1, color='skyblue', edgecolor='black')
ax1.set_title('Load Distribution', fontsize=12, fontweight='bold')
ax1.set_xlabel('Load (MW)')
ax1.set_ylabel('Frequency')
ax1.axvline(load_df['load'].mean(), color='red', linestyle='--', label='Mean')
ax1.axvline(load_df['load'].median(), color='green', linestyle='--', label='Median')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Box plot by month
load_df_with_month = load_df.copy()
load_df_with_month['month'] = load_df_with_month.index.month
load_df_with_month.boxplot(column='load', by='month', ax=ax2)
ax2.set_title('Load Distribution by Month', fontsize=12, fontweight='bold')
ax2.set_xlabel('Month')
ax2.set_ylabel('Load (MW)')
ax2.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
plt.suptitle('')

plt.tight_layout()
plt.savefig(f'{plot_dir}/09_distribution_analysis.png', dpi=150)
plt.close()
print("✓ Saved: 09_distribution_analysis.png")

# ============================================================================
# EDA STEP 10: PEAK DEMAND ANALYSIS
# ============================================================================
print("\n[EDA 10/12] Analyzing peak demand events...")

# Top 20 peak hours
peak_hours = load_df['load'].nlargest(20)

print("\n  Top 20 Peak Demand Hours:")
for i, (timestamp, load) in enumerate(peak_hours.items(), 1):
    print(f"  {i:2d}. {timestamp.strftime('%Y-%m-%d %H:%M')} - {load:.0f} MW")

# Peak by year
load_df_with_year = load_df.copy()
load_df_with_year['year'] = load_df_with_year.index.year
yearly_peaks = load_df_with_year.groupby('year')['load'].max()

fig, ax = plt.subplots(figsize=(10, 5))
yearly_peaks.plot(kind='bar', ax=ax, color='crimson')
ax.set_title('Annual Peak Demand', fontsize=14, fontweight='bold')
ax.set_xlabel('Year')
ax.set_ylabel('Peak Load (MW)')
ax.set_xticklabels(yearly_peaks.index, rotation=0)
ax.grid(True, alpha=0.3, axis='y')

for i, v in enumerate(yearly_peaks):
    ax.text(i, v + 50, f'{v:.0f}', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{plot_dir}/10_peak_demand_analysis.png', dpi=150)
plt.close()
print("✓ Saved: 10_peak_demand_analysis.png")

# ============================================================================
# EDA STEP 11: YEAR-OVER-YEAR COMPARISON
# ============================================================================
print("\n[EDA 11/12] Year-over-year comparison...")

# Average load by year and month
load_df_yoy = load_df.copy()
load_df_yoy['year'] = load_df_yoy.index.year
load_df_yoy['month'] = load_df_yoy.index.month

pivot_yoy = load_df_yoy.pivot_table(values='load', index='month', columns='year', aggfunc='mean')

fig, ax = plt.subplots(figsize=(12, 6))
pivot_yoy.plot(ax=ax, marker='o', linewidth=2)
ax.set_title('Year-over-Year Load Comparison', fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Average Load (MW)')
ax.set_xticks(range(1, 13))
ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
ax.legend(title='Year')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f'{plot_dir}/11_year_over_year.png', dpi=150)
plt.close()
print("✓ Saved: 11_year_over_year.png")

# ============================================================================
# EDA STEP 12: SUMMARY STATISTICS
# ============================================================================
print("\n[EDA 12/12] Computing summary statistics...")

stats = {
    'Count': len(load_df),
    'Mean': load_df['load'].mean(),
    'Median': load_df['load'].median(),
    'Std Dev': load_df['load'].std(),
    'Min': load_df['load'].min(),
    'Max': load_df['load'].max(),
    'Range': load_df['load'].max() - load_df['load'].min(),
    'Q1 (25%)': load_df['load'].quantile(0.25),
    'Q3 (75%)': load_df['load'].quantile(0.75),
    'IQR': load_df['load'].quantile(0.75) - load_df['load'].quantile(0.25),
    'Skewness': load_df['load'].skew(),
    'Kurtosis': load_df['load'].kurtosis()
}

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)
for key, value in stats.items():
    if key == 'Count':
        print(f"{key:15s}: {value:,.0f}")
    else:
        print(f"{key:15s}: {value:,.2f} MW")

# Save summary to file
with open(f'{plot_dir}/summary_statistics.txt', 'w') as f:
    f.write("SLDC DATA 2021-2024 - SUMMARY STATISTICS\n")
    f.write("="*80 + "\n\n")
    for key, value in stats.items():
        if key == 'Count':
            f.write(f"{key:15s}: {value:,.0f}\n")
        else:
            f.write(f"{key:15s}: {value:,.2f} MW\n")

print("\n✓ Saved: summary_statistics.txt")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("EDA COMPLETE!")
print("="*80)
print(f"\n✓ All plots saved to: ${plot_dir}/")
print(f"✓ Clean hourly data saved to: scripts/sldc_hourly_clean.csv")
print(f"\nKey Findings:")
print(f"  • Total hours analyzed: {len(load_df):,}")
print(f"  • Date range: {load_df.index.min().strftime('%Y-%m-%d')} to {load_df.index.max().strftime('%Y-%m-%d')}")
print(f"  • Average load: {load_df['load'].mean():.0f} MW")
print(f"  • Peak load: {load_df['load'].max():.0f} MW")
print(f"  • Peak hour of day: {hourly_profile.idxmax()}:00")
print(f"  • Peak month: {monthly_avg.idxmax()}")
print(f"  • Day-of-week variation: {dow_profile.std():.0f} MW (weak)")
print(f"\nReady for SARIMAX + Transformer modeling! 🚀")
print("="*80)
