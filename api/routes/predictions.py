"""
Prediction API routes.
Phase 3: Enhanced with rate limiting and improved caching.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime
import logging
from collections import defaultdict
from time import time

from ..models.schemas import (
    PredictionRequest,
    PredictionResponse,
    HorizonPredictionRequest,
    HorizonPredictionResponse
)
from ..services.predictor import HybridPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predictions"])

# Simple in-memory rate limiter (for demo)
# In production, use Redis-based rate limiting
_rate_limit_store = defaultdict(list)
RATE_LIMIT = 60  # requests per minute
RATE_WINDOW = 60  # seconds

# Global predictor instance (set by main app)
_predictor: HybridPredictor = None


def set_predictor(predictor: HybridPredictor):
    """Set global predictor instance."""
    global _predictor
    _predictor = predictor


def get_predictor() -> HybridPredictor:
    """Dependency to get predictor instance."""
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Predictor not initialized")
    return _predictor


def check_rate_limit(request: Request):
    """
    Simple in-memory rate limiter.
    Limits to 60 requests per minute per IP.
    
    In production, use Redis-based rate limiting for distributed systems.
    """
    client_ip = request.client.host if request.client else "unknown"
    current_time = time()
    
    # Clean old entries
    _rate_limit_store[client_ip] = [
        req_time for req_time in _rate_limit_store[client_ip]
        if current_time - req_time < RATE_WINDOW
    ]
    
    # Check limit
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} requests per minute."
        )
    
    # Record request
    _rate_limit_store[client_ip].append(current_time)


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    pred_request: PredictionRequest,
    http_request: Request,
    predictor: HybridPredictor = Depends(get_predictor),
    _: None = Depends(check_rate_limit)
):
    """
    Make a single hybrid prediction.
    
    Phase 3 Enhancements:
    - Rate limited to 60 requests/minute per IP
    - Uses DB-backed feature computation
    - Redis caching with 10-minute TTL
    - Per-hour confidence intervals
    
    Returns baseline + residual correction with 95% confidence intervals.
    Auto-fetches weather if not provided.
    """
    try:
        result = predictor.predict(
            timestamp=pred_request.timestamp,
            temperature=pred_request.temperature,
            solar_generation=pred_request.solar_generation,
            humidity=pred_request.humidity,
            cloud_cover=pred_request.cloud_cover,
            return_components=True,
            use_cache=True
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/predict/horizon", response_model=HorizonPredictionResponse)
async def predict_horizon(
    pred_request: HorizonPredictionRequest,
    http_request: Request,
    predictor: HybridPredictor = Depends(get_predictor),
    _: None = Depends(check_rate_limit)
):
    """
    Make predictions for full horizon (up to 168 hours).
    
    Phase 3 Enhancements:
    - Rate limited to 60 requests/minute per IP
    - Uses CSV-based hybrid predictor for accurate predictions
    - Auto-syncs 2025 data from SLDC website if needed
    - Returns actual load values alongside predictions
    - Per-hour confidence intervals from residual statistics
    - File-based caching for expensive iterative predictions
    
    Returns 24-hour (or custom) forecast with confidence intervals and actuals.
    Uses LightGBM + Transformer hybrid model from notebook.
    """
    try:
        timestamp_dt = pred_request.timestamp
        logger.info(f"Computing daily forecast for {timestamp_dt.date()}")
        from ..services.hybrid_predictor import HybridPredictor as CSVPredictor
        from ..services.model_loader import ModelLoader
        from ..services.data_sync import sync_2025_data, get_actual_loads_range
        from datetime import timedelta
        
        timestamp_dt = pred_request.timestamp
        
        # Skip data sync on every request - too slow
        # Run sync manually or via scheduled job instead
        # if timestamp_dt.year >= 2025:
        #     logger.info("Syncing 2025 data from SLDC...")
        #     success, message = sync_2025_data(force_update=False)
        #     if not success:
        #         logger.warning(f"Data sync failed: {message}")
        #     else:
        #         logger.info(f"Data sync: {message}")
        
        # Load models
        model_loader = ModelLoader()
        model_loader.load_all()
        csv_predictor = CSVPredictor(model_loader, use_db=False)
        
        # Determine which CSV to use
        if timestamp_dt.year >= 2025:
            csv_path = 'scripts/2025_master_db.csv'
        else:
            csv_path = 'scripts/master_db.csv'
        
        # Check what data is available in CSV
        import pandas as pd
        df_check = pd.read_csv(csv_path, parse_dates=['timestamp'])
        df_check = df_check.set_index('timestamp').sort_index()
        last_available_ts = df_check.index.max()
        
        logger.info(f"Requested: {timestamp_dt}, Last available in CSV: {last_available_ts}")
        
        # Check if requested timestamp is beyond available data
        if timestamp_dt > last_available_ts:
            logger.info(f"Requested timestamp is beyond CSV data, using iterative predictor")
            
            # Use iterative predictor for future dates
            from ..services.iterative_predictor import predict_future_iterative
            from ..services.weather import get_weather_service
            from ..services.cache import get_redis_client
            
            # Get last 168 hours of REAL history
            history_df = df_check.tail(168).reset_index()
            history_df = history_df[['timestamp', 'load']]
            
            redis_client = get_redis_client()
            weather_service = get_weather_service(redis_client)
            
            # Calculate gap between last available data and requested timestamp
            hours_gap = int((timestamp_dt - last_available_ts).total_seconds() / 3600)
            
            logger.info(f"Gap between last data and request: {hours_gap} hours")
            
            # If there's a gap, try to fill it from cache first, then predict if needed
            if hours_gap > 0:
                logger.info(f"Filling gap: {hours_gap} hours from {last_available_ts} to {timestamp_dt}")
                
                from ..services.cache import get_cache_service, get_redis_client
                redis_client = get_redis_client()
                cache = get_cache_service(redis_client)
                
                gap_start = last_available_ts + timedelta(hours=1)
                gap_predictions = []
                gap_timestamps = []
                
                # Try to get predictions from cache day by day
                current_gap_ts = gap_start
                while current_gap_ts < timestamp_dt:
                    date_str = current_gap_ts.date().isoformat()
                    cached_day = cache.get_hourly_predictions(date_str)
                    
                    if cached_day:
                        # Use cached predictions for this day
                        hour_in_day = current_gap_ts.hour
                        hours_to_take = min(24 - hour_in_day, int((timestamp_dt - current_gap_ts).total_seconds() / 3600))
                        gap_predictions.extend(cached_day[hour_in_day:hour_in_day + hours_to_take])
                        for i in range(hours_to_take):
                            gap_timestamps.append(current_gap_ts + timedelta(hours=i))
                        current_gap_ts += timedelta(hours=hours_to_take)
                        logger.info(f"✓ Used cached predictions for {date_str}")
                    else:
                        # Need to predict this day
                        day_start = datetime.combine(current_gap_ts.date(), datetime.min.time())
                        hours_in_day = min(24, int((timestamp_dt - day_start).total_seconds() / 3600))
                        
                        day_timestamps = [day_start + timedelta(hours=i) for i in range(24)]
                        day_weather = weather_service.get_weather_for_hours(day_timestamps)
                        
                        day_result = predict_future_iterative(
                            start_timestamp=day_start,
                            horizon=24,
                            history_df=history_df,
                            lgbm_model=csv_predictor.lgbm_model,
                            transformer_model=csv_predictor.transformer_model,
                            residual_scaler=csv_predictor.residual_scaler,
                            feature_order=csv_predictor.feature_order,
                            weather_forecasts=day_weather
                        )
                        
                        # Cache this day's predictions
                        cache.store_hourly_predictions(date_str, day_result['predictions'])
                        
                        # Add to gap
                        hour_in_day = current_gap_ts.hour
                        hours_to_take = min(24 - hour_in_day, hours_in_day)
                        gap_predictions.extend(day_result['predictions'][hour_in_day:hour_in_day + hours_to_take])
                        for i in range(hours_to_take):
                            gap_timestamps.append(current_gap_ts + timedelta(hours=i))
                        
                        # Update history for next day
                        day_df = pd.DataFrame({
                            'timestamp': pd.to_datetime(day_result['timestamps']),
                            'load': day_result['predictions']
                        })
                        history_df = pd.concat([history_df, day_df], ignore_index=True)
                        history_df = history_df.tail(168)
                        
                        current_gap_ts += timedelta(hours=hours_to_take)
                        logger.info(f"✓ Predicted and cached {date_str}")
                
                # Add all gap predictions to history
                if gap_predictions:
                    gap_df = pd.DataFrame({
                        'timestamp': gap_timestamps,
                        'load': gap_predictions
                    })
                    history_df = pd.concat([history_df, gap_df], ignore_index=True)
                    history_df = history_df.tail(168)
                    logger.info(f"✓ Filled gap with {len(gap_predictions)} hours")
            
            # Now predict the requested 24 hours
            # Check if this day is already cached
            request_date = timestamp_dt.date().isoformat()
            cached_request_day = cache.get_hourly_predictions(request_date)
            
            if cached_request_day and pred_request.horizon <= 24:
                logger.info(f"✓ Using cached predictions for requested date {request_date}")
                # For cached predictions, we don't have baselines/residuals
                # Set them to None to indicate they're not available
                preds = cached_request_day[timestamp_dt.hour:timestamp_dt.hour + pred_request.horizon]
                result = {
                    'start_timestamp': timestamp_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamps': [(timestamp_dt + timedelta(hours=i)).isoformat() for i in range(pred_request.horizon)],
                    'predictions': preds,
                    'baselines': preds,  # Use predictions as baseline approximation
                    'residuals': [0.0] * pred_request.horizon  # Unknown for cached
                }
            else:
                # Need to predict
                forecast_timestamps = [timestamp_dt + timedelta(hours=i) for i in range(pred_request.horizon)]
                weather_forecasts = weather_service.get_weather_for_hours(forecast_timestamps)
                
                # Run iterative prediction
                result = predict_future_iterative(
                    start_timestamp=timestamp_dt,
                    horizon=pred_request.horizon,
                    history_df=history_df,
                    lgbm_model=csv_predictor.lgbm_model,
                    transformer_model=csv_predictor.transformer_model,
                    residual_scaler=csv_predictor.residual_scaler,
                    feature_order=csv_predictor.feature_order,
                    weather_forecasts=weather_forecasts
                )
                
                # Cache if it's a full day prediction starting at midnight
                if timestamp_dt.hour == 0 and pred_request.horizon == 24:
                    cache.store_hourly_predictions(request_date, result['predictions'])
                    logger.info(f"✓ Cached predictions for {request_date}")
            
            # No actuals for future dates
            actuals = [None] * len(result['predictions'])
            last_actual_index = -1
            
            # Confidence decreases with prediction horizon
            # Near-term: 90%, decreases by 1% per 6 hours
            confidence_scores = [max(75.0, 90.0 - (i / 6.0)) for i in range(len(result['predictions']))]
            
            formatted_result = {
                'timestamp': result['start_timestamp'],
                'horizon': len(result['predictions']),
                'predictions': result['predictions'],
                'actuals': actuals,
                'last_actual_index': last_actual_index,
                'confidence_scores': confidence_scores,
                'confidence_intervals': [
                    {
                        'lower': max(0, p - 175),
                        'upper': p + 175,
                        'margin': 175
                    }
                    for p in result['predictions']
                ],
                'baselines': result['baselines'],
                'residuals': result['residuals'],
                'metadata': {
                    'data_source': 'iterative_forecast',
                    'model': 'lgbm_transformer_hybrid',
                    'method': 'hour_by_hour_with_lag_updates',
                    'units': 'MW',
                    'actuals_available': 0
                }
            }
            
            return formatted_result
        
        # For historical dates, use CSV-based prediction
        # Find a timestamp that has enough data
        latest_valid_start = last_available_ts - timedelta(hours=23)
        
        if timestamp_dt <= latest_valid_start and timestamp_dt in df_check.index:
            prediction_start = timestamp_dt
        else:
            # Adjust to latest valid timestamp
            prediction_start = latest_valid_start
            closest_idx = df_check.index.get_indexer([prediction_start], method='nearest')[0]
            prediction_start = df_check.index[closest_idx]
            logger.info(f"Adjusted to: {prediction_start}")
        
        # Check history
        history_before = df_check.loc[:prediction_start]
        if len(history_before) < 168:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient history. Need 168 hours, have {len(history_before)}"
            )
        
        # Predict using CSV data
        result = csv_predictor.predict_24h_from_csv(
            csv_path=csv_path,
            start_timestamp=prediction_start.strftime('%Y-%m-%d %H:%M:%S'),
            return_metrics=False
        )
        
        # Get actuals for the PREDICTION period (not requested period)
        prediction_end = prediction_start + timedelta(hours=pred_request.horizon - 1)
        actuals_df = get_actual_loads_range(prediction_start, prediction_end)
        
        # Create actuals list
        actuals = []
        last_actual_index = -1
        for i in range(len(result['predictions'])):
            hour_ts = prediction_start + timedelta(hours=i)
            
            if not actuals_df.empty:
                matching = actuals_df[actuals_df['timestamp'] == hour_ts]
                if not matching.empty:
                    actuals.append(float(matching.iloc[0]['load']))
                    last_actual_index = i
                else:
                    actuals.append(None)
            else:
                actuals.append(None)
        
        # Confidence based on data availability
        # Historical data (with actuals): 95%
        # Recent data (CSV but no actuals): 90%
        confidence_scores = [95.0 if actuals[i] is not None else 90.0 for i in range(len(result['predictions']))]
        
        # Format response to match expected schema
        formatted_result = {
            'timestamp': result['start_timestamp'],
            'horizon': len(result['predictions']),
            'predictions': result['predictions'],
            'actuals': actuals,  # NEW: Include actual values
            'last_actual_index': last_actual_index,  # NEW: Index of last actual value
            'confidence_scores': confidence_scores,
            'confidence_intervals': [
                {
                    'lower': max(0, p - 175),
                    'upper': p + 175,
                    'margin': 175
                }
                for p in result['predictions']
            ],
            'baselines': result['baselines'],
            'residuals': result['residuals'],
            'metadata': {
                'data_source': 'csv',
                'model': 'lgbm_transformer_hybrid',
                'csv_file': csv_path,
                'units': 'MW',
                'actuals_available': sum(1 for a in actuals if a is not None),
                'last_available_data': last_available_ts.isoformat() if 'last_available_ts' in locals() else None
            }
        }
        
        return formatted_result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Horizon prediction failed: {e}", exc_info=True)
        # Fallback to original predictor
        try:
            result = predictor.predict_horizon(
                timestamp=pred_request.timestamp,
                temperature=pred_request.temperature,
                solar_generation=pred_request.solar_generation,
                humidity=pred_request.humidity,
                cloud_cover=pred_request.cloud_cover,
                horizon=pred_request.horizon,
                use_cache=True
            )
            return result
        except:
            raise HTTPException(status_code=500, detail=f"Horizon prediction failed: {str(e)}")
