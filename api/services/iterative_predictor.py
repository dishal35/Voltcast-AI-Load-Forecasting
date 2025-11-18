"""
Iterative Predictor for Future Dates
Implements hour-by-hour prediction with lag feature updates.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
import holidays

logger = logging.getLogger(__name__)


def heat_index_safe(temp_c, rh):
    """NOAA heat index calculation."""
    T = temp_c * 9/5 + 32
    HI = (-42.379 + 2.04901523*T + 10.14333127*rh - 0.22475541*T*rh
          - .00683783*T*T - .05481717*rh*rh + .00122874*T*T*rh
          + .00085282*T*rh*rh - .00000199*T*T*rh*rh)
    simple = 0.5*(T + 61 + (T-68)*1.2 + rh*0.094)
    HI = np.where(T < 80, simple, HI)
    return (HI - 32) * 5/9


def build_feature_row(
    timestamp: datetime,
    history_df: pd.DataFrame,
    weather: Dict,
    feature_order: List[str]
) -> np.ndarray:
    """
    Build a single feature row for prediction.
    
    Args:
        timestamp: Timestamp to predict for
        history_df: DataFrame with columns ['timestamp', 'load'] containing history
        weather: Dict with weather features
        feature_order: List of feature names in correct order
    
    Returns:
        Feature vector as numpy array
    """
    features = {}
    
    # Time features
    hols = holidays.India(years=[timestamp.year])
    features['is_holiday'] = 1 if timestamp.date() in hols else 0
    features['dow'] = timestamp.weekday()
    features['hour'] = timestamp.hour
    features['is_weekend'] = 1 if timestamp.weekday() >= 5 else 0
    features['month'] = timestamp.month
    features['hour_of_week'] = timestamp.weekday() * 24 + timestamp.hour
    
    # Weather features
    features['temperature_2m'] = weather.get('temperature', 25.0)
    features['relativehumidity_2m'] = weather.get('humidity', 60.0)
    features['apparent_temperature'] = weather.get('apparent_temperature', 
                                                   features['temperature_2m'])
    features['shortwave_radiation'] = weather.get('solar_radiation', 50.0)
    features['precipitation'] = weather.get('precipitation', 0.0)
    features['wind_speed_10m'] = weather.get('wind_speed', 3.5)
    
    # Heat index
    features['heat_index'] = heat_index_safe(
        features['temperature_2m'],
        features['relativehumidity_2m']
    )
    
    # Lag features from history
    # Sort history by timestamp
    hist_sorted = history_df.sort_values('timestamp')
    
    # lag_1: load 1 hour ago
    lag_1_ts = timestamp - timedelta(hours=1)
    lag_1_row = hist_sorted[hist_sorted['timestamp'] == lag_1_ts]
    features['lag_1'] = lag_1_row['load'].iloc[0] if not lag_1_row.empty else hist_sorted['load'].iloc[-1]
    
    # lag_24: load 24 hours ago
    lag_24_ts = timestamp - timedelta(hours=24)
    lag_24_row = hist_sorted[hist_sorted['timestamp'] == lag_24_ts]
    features['lag_24'] = lag_24_row['load'].iloc[0] if not lag_24_row.empty else features['lag_1']
    
    # lag_168: load 168 hours ago
    lag_168_ts = timestamp - timedelta(hours=168)
    lag_168_row = hist_sorted[hist_sorted['timestamp'] == lag_168_ts]
    features['lag_168'] = lag_168_row['load'].iloc[0] if not lag_168_row.empty else features['lag_24']
    
    # Rolling means
    # roll24: mean of last 24 hours
    last_24h = hist_sorted[hist_sorted['timestamp'] > (timestamp - timedelta(hours=24))]
    features['roll24'] = last_24h['load'].mean() if len(last_24h) > 0 else features['lag_1']
    
    # roll168: mean of last 168 hours
    last_168h = hist_sorted[hist_sorted['timestamp'] > (timestamp - timedelta(hours=168))]
    features['roll168'] = last_168h['load'].mean() if len(last_168h) > 0 else features['roll24']
    
    # Build vector in correct order
    vector = np.array([features.get(feat, 0.0) for feat in feature_order], dtype=np.float32)
    
    return vector


def predict_future_iterative(
    start_timestamp: datetime,
    horizon: int,
    history_df: pd.DataFrame,
    lgbm_model,
    transformer_model,
    residual_scaler,
    feature_order: List[str],
    weather_forecasts: List[Dict]
) -> Dict:
    """
    Predict future load iteratively, updating lags with predictions.
    
    Args:
        start_timestamp: Starting timestamp for predictions
        horizon: Number of hours to predict
        history_df: DataFrame with at least 168 hours of history (columns: timestamp, load)
        lgbm_model: Trained LightGBM model
        transformer_model: Trained Transformer model
        residual_scaler: Scaler for residuals
        feature_order: List of feature names
        weather_forecasts: List of weather dicts for each hour
    
    Returns:
        Dict with predictions, baselines, residuals
    """
    logger.info(f"Starting iterative prediction from {start_timestamp} for {horizon} hours")
    
    # Initialize results
    predictions = []
    baselines = []
    residuals = []
    timestamps = []
    
    # Create working history (will be updated with predictions)
    working_history = history_df.copy()
    
    # Get initial residual sequence for transformer (last 168 hours)
    if transformer_model is not None and residual_scaler is not None:
        # Compute residuals from history
        hist_features = []
        for idx in range(max(0, len(working_history) - 168), len(working_history)):
            row = working_history.iloc[idx]
            # Build features for this historical point
            weather_hist = {
                'temperature': row.get('temperature_2m', 25.0),
                'humidity': row.get('relativehumidity_2m', 60.0),
                'wind_speed': row.get('wind_speed_10m', 3.5),
                'solar_radiation': row.get('shortwave_radiation', 50.0),
                'precipitation': row.get('precipitation', 0.0)
            }
            feat_vec = build_feature_row(row['timestamp'], working_history.iloc[:idx+1], 
                                        weather_hist, feature_order)
            hist_features.append(feat_vec)
        
        # Get LGBM predictions for history
        if len(hist_features) > 0:
            hist_features_array = np.array(hist_features)
            hist_baselines = lgbm_model.predict(hist_features_array)
            hist_actuals = working_history.iloc[-len(hist_baselines):]['load'].values
            hist_residuals = hist_actuals - hist_baselines
            
            # Scale residuals
            residual_sequence = residual_scaler.transform(hist_residuals.reshape(-1, 1)).flatten()
            residual_sequence = residual_sequence[-168:]  # Last 168
        else:
            residual_sequence = np.zeros(168)
    else:
        residual_sequence = None
    
    # Predict hour by hour
    current_ts = start_timestamp
    
    # Debug: Log first hour features
    if horizon > 0:
        logger.info(f"First prediction timestamp: {current_ts}")
        logger.info(f"  DOW: {current_ts.weekday()}, Hour: {current_ts.hour}")
        logger.info(f"  History size: {len(working_history)} rows")
        logger.info(f"  Last history timestamp: {working_history['timestamp'].iloc[-1]}")
    
    for hour_idx in range(horizon):
        # Get weather for this hour
        weather = weather_forecasts[hour_idx] if hour_idx < len(weather_forecasts) else {}
        
        # Debug: Log weather for first hour
        if hour_idx == 0:
            logger.info(f"  Weather: temp={weather.get('temperature', 'N/A')}, "
                       f"humidity={weather.get('humidity', 'N/A')}")
        
        # Build features using current history
        feature_vector = build_feature_row(current_ts, working_history, weather, feature_order)
        
        # LGBM baseline prediction
        baseline = lgbm_model.predict(feature_vector.reshape(1, -1))[0]
        baseline = float(baseline)
        
        # Transformer residual prediction
        residual = 0.0
        if transformer_model is not None and residual_sequence is not None and len(residual_sequence) >= 168:
            import torch
            seq_tensor = torch.tensor(residual_sequence[-168:], dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
            
            with torch.no_grad():
                residual_scaled = transformer_model(seq_tensor).item()
            
            # Unscale
            residual = residual_scaler.inverse_transform([[residual_scaled]])[0][0]
            residual = float(residual)
            
            # Update residual sequence for next iteration
            residual_sequence = np.append(residual_sequence[1:], residual_scaled)
        
        # Hybrid prediction
        prediction = baseline + residual
        prediction = max(0.0, prediction)
        
        # Store results
        predictions.append(prediction)
        baselines.append(baseline)
        residuals.append(residual)
        timestamps.append(current_ts.isoformat())
        
        # CRITICAL: Add prediction to history for next iteration
        new_row = pd.DataFrame({
            'timestamp': [current_ts],
            'load': [prediction],
            'temperature_2m': [weather.get('temperature', 25.0)],
            'relativehumidity_2m': [weather.get('humidity', 60.0)],
            'wind_speed_10m': [weather.get('wind_speed', 3.5)],
            'shortwave_radiation': [weather.get('solar_radiation', 50.0)],
            'precipitation': [weather.get('precipitation', 0.0)]
        })
        working_history = pd.concat([working_history, new_row], ignore_index=True)
        
        # Move to next hour
        current_ts += timedelta(hours=1)
        
        if (hour_idx + 1) % 6 == 0:
            logger.info(f"  Predicted {hour_idx + 1}/{horizon} hours")
    
    logger.info(f"✓ Completed iterative prediction")
    
    return {
        'start_timestamp': start_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamps': timestamps,
        'predictions': predictions,
        'baselines': baselines,
        'residuals': residuals
    }
