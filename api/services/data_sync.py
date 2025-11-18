"""
Data Synchronization Service
Fetches real-time SLDC load data and weather data to keep 2025_master_db.csv updated.
Ensures lag features are properly computed for accurate predictions.
"""
import pandas as pd
import numpy as np
import requests
import holidays
from datetime import datetime, timedelta, date
from bs4 import BeautifulSoup
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
LAT = 28.7041  # Delhi coordinates
LON = 77.1025
TZ = "Asia/Kolkata"
CSV_PATH_2024 = "scripts/master_db.csv"
CSV_PATH_2025 = "scripts/2025_master_db.csv"
SLDC_RAW_PATH = "scripts/2025_sldc_raw.csv"


def heat_index_safe(temp_c, rh):
    """
    NOAA heat index calculation (must match training code).
    """
    T = temp_c * 9/5 + 32
    HI = (-42.379 + 2.04901523*T + 10.14333127*rh - 0.22475541*T*rh
          - .00683783*T*T - .05481717*rh*rh + .00122874*T*T*rh
          + .00085282*T*rh*rh - .00000199*T*T*rh*rh)
    simple = 0.5*(T + 61 + (T-68)*1.2 + rh*0.094)
    
    HI = np.where(T < 80, simple, HI)
    return (HI - 32) * 5/9


def scrape_sldc_day(target_date: date) -> pd.DataFrame:
    """
    Scrape SLDC data for a specific day.
    
    Args:
        target_date: Date to scrape
    
    Returns:
        DataFrame with timestamp and load columns
    """
    url = 'http://www.delhisldc.org/Loaddata.aspx?mode='
    date_str = target_date.strftime('%d/%m/%Y')
    
    try:
        resp = requests.get(url + date_str, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'lxml')
        table = soup.find('table', {'id': 'ContentPlaceHolder3_DGGridAv'})
        
        if not table:
            logger.warning(f"No table found for {date_str}")
            return pd.DataFrame()
        
        all_data = []
        trs = table.find_all('tr')
        
        for tr in trs[1:]:  # Skip header
            fonts = tr.find_all('font')[:7]
            
            if len(fonts) >= 2:
                time_val = fonts[0].text.strip()
                delhi = fonts[1].text.strip()
                
                timestamp_str = f"{date_str} {time_val}"
                
                try:
                    all_data.append({
                        'timestamp': pd.to_datetime(timestamp_str, format='%d/%m/%Y %H:%M'),
                        'load': float(delhi) if delhi else np.nan
                    })
                except (ValueError, AttributeError):
                    continue
        
        return pd.DataFrame(all_data)
    
    except Exception as e:
        logger.error(f"Failed to scrape {date_str}: {e}")
        return pd.DataFrame()


def fetch_sldc_range(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Fetch SLDC data for a date range.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        DataFrame with hourly load data
    """
    logger.info(f"Fetching SLDC data from {start_date} to {end_date}")
    
    all_data = []
    current_date = start_date
    delta = timedelta(days=1)
    
    while current_date <= end_date:
        day_data = scrape_sldc_day(current_date)
        if not day_data.empty:
            all_data.append(day_data)
            logger.info(f"  ✓ {current_date}: {len(day_data)} records")
        else:
            logger.warning(f"  ✗ {current_date}: No data")
        
        current_date += delta
        time.sleep(0.2)  # Be polite to server
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine and aggregate to hourly
    df = pd.concat(all_data, ignore_index=True)
    df = df.set_index('timestamp').sort_index()
    
    # Resample to hourly
    hourly = df.resample('h').agg({'load': ['mean', 'count']})
    hourly.columns = ['load', 'load_count']
    
    # Filter out hours with insufficient data (< 10 5-minute records)
    hourly.loc[hourly['load_count'] < 10, 'load'] = np.nan
    hourly = hourly[['load']]
    
    logger.info(f"Aggregated to {len(hourly)} hourly records")
    
    return hourly


def fetch_weather_range(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch weather data from Open-Meteo API.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        DataFrame with hourly weather data
    """
    logger.info(f"Fetching weather data from {start_date} to {end_date}")
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relativehumidity_2m,apparent_temperature,"
                  "shortwave_radiation,precipitation,wind_speed_10m",
        "timezone": TZ
    }
    
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        js = r.json()["hourly"]
        
        df = pd.DataFrame(js)
        df['timestamp'] = pd.to_datetime(df['time'])
        df = df.set_index('timestamp').drop(columns=['time'])
        
        logger.info(f"Fetched {len(df)} hourly weather records")
        return df
    
    except Exception as e:
        logger.error(f"Failed to fetch weather: {e}")
        return pd.DataFrame()


def compute_features(df: pd.DataFrame, hist_2024: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all required features matching training data.
    
    Args:
        df: DataFrame with load and weather data
        hist_2024: Last 168 hours of 2024 data for lag initialization
    
    Returns:
        DataFrame with all features
    """
    logger.info("Computing features...")
    
    # Time features
    hols = holidays.India(years=[2025])
    df['is_holiday'] = [1 if d.date() in hols else 0 for d in df.index]
    df['dow'] = df.index.dayofweek
    df['hour'] = df.index.hour
    df['is_weekend'] = df['dow'].isin([5, 6]).astype(int)
    df['month'] = df.index.month
    
    # Heat index
    df['heat_index'] = heat_index_safe(
        df['temperature_2m'].ffill(),
        df['relativehumidity_2m'].ffill()
    )
    
    # Fill missing load values before computing lags
    missing_load = df['load'].isna().sum()
    if missing_load > 0:
        logger.info(f"Filling {missing_load} missing load values...")
        how = df.index.dayofweek * 24 + df.index.hour
        df['load'] = df['load'].fillna(df.groupby(how)['load'].transform('median'))
        df['load'] = df['load'].interpolate(method='linear', limit=6)
        df['load'] = df['load'].ffill().bfill()
    
    # Compute lags using 2024 history
    full = pd.concat([hist_2024[['load']], df[['load']]], axis=0)
    full = full.sort_index()
    
    full['lag_1'] = full['load'].shift(1)
    full['lag_24'] = full['load'].shift(24)
    full['lag_168'] = full['load'].shift(168)
    full['roll24'] = full['load'].rolling(24).mean().shift(1)
    full['roll168'] = full['load'].rolling(168).mean().shift(1)
    
    # Extract computed lags for 2025 data
    df['lag_1'] = full.loc[df.index, 'lag_1']
    df['lag_24'] = full.loc[df.index, 'lag_24']
    df['lag_168'] = full.loc[df.index, 'lag_168']
    df['roll24'] = full.loc[df.index, 'roll24']
    df['roll168'] = full.loc[df.index, 'roll168']
    
    logger.info("✓ Features computed")
    
    return df


def sync_2025_data(force_update: bool = False) -> Tuple[bool, str]:
    """
    Synchronize 2025 data: fetch missing SLDC + weather data and update CSV.
    
    Args:
        force_update: If True, fetch data even if CSV is up-to-date
    
    Returns:
        Tuple of (success, message)
    """
    try:
        logger.info("="*60)
        logger.info("DATA SYNC: Updating 2025 Master DB")
        logger.info("="*60)
        
        # Load existing 2025 data
        csv_path = Path(CSV_PATH_2025)
        if csv_path.exists():
            existing_df = pd.read_csv(csv_path, parse_dates=['timestamp'])
            existing_df = existing_df.set_index('timestamp').sort_index()
            last_timestamp = existing_df.index.max()
            logger.info(f"Existing data: {len(existing_df)} hours, last: {last_timestamp}")
        else:
            existing_df = pd.DataFrame()
            last_timestamp = pd.Timestamp('2024-12-31 23:00:00')
            logger.info("No existing 2025 data found")
        
        # Determine what data to fetch
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Start from day after last data (or Jan 1, 2025)
        if not existing_df.empty:
            fetch_start = (last_timestamp + timedelta(hours=1)).date()
        else:
            fetch_start = date(2025, 1, 1)
        
        # End at current hour
        fetch_end = current_hour.date()
        
        # Check if update needed
        if fetch_start > fetch_end and not force_update:
            logger.info("Data is up-to-date, no sync needed")
            return True, "Data is up-to-date"
        
        logger.info(f"Fetching data from {fetch_start} to {fetch_end}")
        
        # Fetch SLDC data
        sldc_data = fetch_sldc_range(fetch_start, fetch_end)
        if sldc_data.empty:
            return False, "Failed to fetch SLDC data"
        
        # Fetch weather data
        weather_data = fetch_weather_range(
            fetch_start.strftime('%Y-%m-%d'),
            fetch_end.strftime('%Y-%m-%d')
        )
        if weather_data.empty:
            return False, "Failed to fetch weather data"
        
        # Create master DataFrame for new data
        start_ts = pd.Timestamp(f'{fetch_start} 00:00:00')
        end_ts = pd.Timestamp(f'{fetch_end} {current_hour.hour}:00:00')
        
        new_df = pd.DataFrame(index=pd.date_range(start=start_ts, end=end_ts, freq='h'))
        new_df.index.name = 'timestamp'
        
        # Join load and weather
        new_df = new_df.join(sldc_data, how='left')
        new_df = new_df.join(weather_data, how='left')
        
        # Forward-fill weather
        for col in ['temperature_2m', 'relativehumidity_2m', 'apparent_temperature',
                    'shortwave_radiation', 'precipitation', 'wind_speed_10m']:
            if col in new_df.columns:
                new_df[col] = new_df[col].ffill().bfill()
        
        # Load 2024 history for lag computation
        hist_2024_path = Path(CSV_PATH_2024)
        if not hist_2024_path.exists():
            return False, "2024 master_db.csv not found - needed for lag features"
        
        hist_2024 = pd.read_csv(hist_2024_path, parse_dates=['timestamp'])
        hist_2024 = hist_2024.set_index('timestamp').sort_index()
        hist_2024 = hist_2024.loc[:'2024-12-31 23:00:00']  # Only 2024 data
        hist_tail = hist_2024.tail(168)  # Last 7 days
        
        # Compute features
        new_df = compute_features(new_df, hist_tail)
        
        # Combine with existing data
        if not existing_df.empty:
            # Merge, preferring new data for overlaps
            combined = pd.concat([existing_df, new_df])
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
        else:
            combined = new_df
        
        # Ensure correct column order
        column_order = [
            'load', 'temperature_2m', 'relativehumidity_2m', 'apparent_temperature',
            'shortwave_radiation', 'precipitation', 'wind_speed_10m', 'is_holiday',
            'dow', 'hour', 'is_weekend', 'month', 'heat_index',
            'lag_1', 'lag_24', 'lag_168', 'roll24', 'roll168'
        ]
        
        final_df = combined[column_order].copy()
        final_df = final_df.reset_index()
        final_df = final_df[['timestamp'] + column_order]
        
        # Save to CSV
        final_df.to_csv(csv_path, index=False)
        
        # Invalidate cache for updated dates
        try:
            from .cache import get_cache_service, get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                cache = get_cache_service(redis_client)
                # Invalidate cache for the date range that was updated
                invalidated = cache.invalidate_date_range(
                    fetch_start.isoformat(),
                    fetch_end.isoformat()
                )
                if invalidated > 0:
                    logger.info(f"✓ Invalidated {invalidated} cached predictions")
        except Exception as e:
            logger.warning(f"Cache invalidation failed (non-critical): {e}")
        
        logger.info("="*60)
        logger.info(f"✓ Data sync complete!")
        logger.info(f"  Total records: {len(final_df)}")
        logger.info(f"  Date range: {final_df['timestamp'].min()} → {final_df['timestamp'].max()}")
        logger.info(f"  New records added: {len(new_df)}")
        logger.info("="*60)
        
        return True, f"Successfully synced {len(new_df)} new records"
    
    except Exception as e:
        logger.error(f"Data sync failed: {e}", exc_info=True)
        return False, f"Data sync failed: {str(e)}"


def get_actual_load(timestamp: datetime) -> Optional[float]:
    """
    Get actual load value for a specific timestamp.
    Only returns actual if timestamp is in the past or current hour.
    
    Args:
        timestamp: Timestamp to get load for
    
    Returns:
        Load value in MW, or None if not available or in the future
    """
    try:
        # Get current time (round down to hour)
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # If timestamp is in the future, return None
        if timestamp > now:
            return None
        
        # Determine which CSV to use
        if timestamp.year >= 2025:
            csv_path = CSV_PATH_2025
        else:
            csv_path = CSV_PATH_2024
        
        df = pd.read_csv(csv_path, parse_dates=['timestamp'])
        df = df.set_index('timestamp')
        
        if timestamp in df.index:
            return float(df.loc[timestamp, 'load'])
        else:
            return None
    
    except Exception as e:
        logger.error(f"Failed to get actual load for {timestamp}: {e}")
        return None


def get_actual_loads_range(start_ts: datetime, end_ts: datetime) -> pd.DataFrame:
    """
    Get actual load values for a time range.
    Only returns actuals for timestamps that have already occurred (past or current hour).
    
    Args:
        start_ts: Start timestamp
        end_ts: End timestamp
    
    Returns:
        DataFrame with timestamp and load columns (only for past/current timestamps)
    """
    try:
        # Get current time (round down to hour)
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Only get actuals up to current hour
        actual_end_ts = min(end_ts, now)
        
        # If start is in the future, return empty DataFrame
        if start_ts > now:
            logger.info(f"Start timestamp {start_ts} is in the future, no actuals available")
            return pd.DataFrame()
        
        # Determine which CSV(s) to use
        if start_ts.year >= 2025:
            csv_path = CSV_PATH_2025
        else:
            csv_path = CSV_PATH_2024
        
        df = pd.read_csv(csv_path, parse_dates=['timestamp'])
        df = df.set_index('timestamp').sort_index()
        
        # Filter to range (only up to current hour)
        mask = (df.index >= start_ts) & (df.index <= actual_end_ts)
        result = df.loc[mask, ['load']].copy()
        result = result.reset_index()
        
        logger.info(f"Retrieved {len(result)} actual values from {start_ts} to {actual_end_ts}")
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to get actual loads for range: {e}")
        return pd.DataFrame()
