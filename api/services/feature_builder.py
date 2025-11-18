"""
Feature Builder Service
Reconstructs engineered features in the exact order used during training.
Phase 2: Uses real historical data from database for accurate feature computation.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """Builds feature vectors matching training feature order."""
    
    def __init__(
        self, 
        feature_order_path: str = None, 
        scaler=None, 
        feature_order: list = None,
        storage_service=None,
        historical_averages: Dict = None
    ):
        """
        Initialize feature builder.
        
        Args:
            feature_order_path: Path to feature_order.json (optional if feature_order provided)
            scaler: Optional sklearn scaler (RobustScaler)
            feature_order: Optional pre-loaded feature order list
            storage_service: Storage service for historical data (optional)
            historical_averages: Dict of fallback values from training (optional)
        """
        if feature_order is not None:
            self.feature_order = feature_order
        elif feature_order_path is not None:
            with open(feature_order_path) as f:
                data = json.load(f)
                self.feature_order = data.get("feature_order", data) if isinstance(data, dict) else data
        else:
            raise ValueError("Either feature_order_path or feature_order must be provided")
        
        self.scaler = scaler
        self.n_features = len(self.feature_order)
        self.storage_service = storage_service
        self.historical_averages = historical_averages or self._load_historical_averages()
    
    def _load_historical_averages(self) -> Dict:
        """Load historical averages from final_report.json for fallback."""
        try:
            report_path = Path('artifacts') / 'final_report.json'
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                    return report.get('historical_averages', {})
        except Exception as e:
            logger.warning(f"Could not load historical averages: {e}")
        
        # Default fallback
        return {
            'demand': 3000.0,
            'temperature': 25.0,
            'humidity': 60.0,
            'wind_speed': 3.5,
            'cloud_cover': 40.0,
            'solar_generation': 50.0
        }
    
    def build_from_raw(
        self,
        timestamp: datetime,
        temperature: float,
        solar_generation: float,
        humidity: Optional[float] = None,
        cloud_cover: Optional[float] = None,
        demand_history: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Build features from raw inputs.
        
        Args:
            timestamp: Datetime of prediction
            temperature: Temperature in °C
            solar_generation: Solar generation in MW
            humidity: Humidity percentage (optional)
            cloud_cover: Cloud cover percentage (optional)
            demand_history: Historical demand values (optional)
        
        Returns:
            Dictionary of feature name -> value
        """
        features = {}
        
        # Temporal features
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        day_of_year = timestamp.timetuple().tm_yday
        month = timestamp.month
        
        # Cyclical encoding
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        features['dow_cos'] = np.cos(2 * np.pi * day_of_week / 7)
        features['dow_sin'] = np.sin(2 * np.pi * day_of_week / 7)
        features['doy_cos'] = np.cos(2 * np.pi * day_of_year / 365)
        features['doy_sin'] = np.sin(2 * np.pi * day_of_year / 365)
        features['month_cos'] = np.cos(2 * np.pi * month / 12)
        features['month_sin'] = np.sin(2 * np.pi * month / 12)
        
        # Weather features
        features['temperature'] = temperature
        features['solar_generation'] = solar_generation
        features['humidity'] = humidity if humidity is not None else 50.0
        features['cloud_cover'] = cloud_cover if cloud_cover is not None else 50.0
        
        # Derived weather features
        features['temp_solar_interaction'] = temperature * solar_generation / 100.0
        features['temp_humidity_interaction'] = temperature * (humidity if humidity else 50.0) / 100.0
        features['heat_index'] = temperature + 0.5555 * ((humidity if humidity else 50.0) / 100.0 * 6.11 * np.exp(5417.7530 * (1/273.16 - 1/(273.15 + temperature))) - 10)
        
        # Weekend and holiday flags
        features['is_weekend'] = 1 if day_of_week >= 5 else 0
        features['is_holiday'] = 0  # Would need holiday calendar
        
        # Placeholder for lag/rolling features (would need historical data)
        # For now, use zeros or simple estimates
        lag_features = [
            'demand_lag_1', 'demand_lag_2', 'demand_lag_3', 'demand_lag_6',
            'demand_lag_12', 'demand_lag_24', 'demand_lag_48', 'demand_lag_72',
            'demand_lag_168'
        ]
        for feat in lag_features:
            features[feat] = 0.0
        
        # Temperature lags (simple assumption: same as current)
        temp_lags = ['temp_lag_1', 'temp_lag_2', 'temp_lag_3', 'temp_lag_6',
                     'temp_lag_12', 'temp_lag_24', 'temp_lag_48', 'temp_lag_72', 'temp_lag_168']
        for feat in temp_lags:
            features[feat] = temperature
        
        # Rolling statistics (placeholders)
        rolling_features = [
            'demand_roll_mean_6', 'demand_roll_std_6', 'demand_roll_q25_6', 'demand_roll_q75_6',
            'demand_roll_mean_12', 'demand_roll_std_12', 'demand_roll_q25_12', 'demand_roll_q75_12',
            'demand_roll_mean_24', 'demand_roll_std_24', 'demand_roll_q25_24', 'demand_roll_q75_24',
            'demand_roll_mean_168', 'demand_roll_std_168', 'demand_roll_q25_168', 'demand_roll_q75_168'
        ]
        for feat in rolling_features:
            features[feat] = 0.0
        
        # Differences (placeholders)
        features['demand_diff_1h'] = 0.0
        features['demand_diff_24h'] = 0.0
        features['demand_diff2_1h'] = 0.0
        
        # FFT components (placeholders)
        features['fft_amp_1_168'] = 0.0
        features['fft_amp_2_168'] = 0.0
        features['fft_amp_3_168'] = 0.0
        
        # Holiday distance features
        features['days_since_last_holiday'] = 30.0
        features['days_to_next_holiday'] = 30.0
        
        return features
    
    def build_vector(self, features: Dict[str, float]) -> np.ndarray:
        """
        Build feature vector in correct order.
        
        Args:
            features: Dictionary of feature name -> value
        
        Returns:
            Numpy array of shape (n_features,)
        """
        vector = np.zeros(self.n_features, dtype=np.float32)
        
        for i, feat_name in enumerate(self.feature_order):
            vector[i] = features.get(feat_name, 0.0)
        
        return vector
    
    def build_sequence(
        self,
        features: Dict[str, float],
        seq_len: int = 168,
        residuals: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Build transformer sequence.
        For LightGBM+Transformer model, this should be residuals, not features.
        
        Args:
            features: Dictionary of feature name -> value (used if residuals not provided)
            seq_len: Sequence length (default 168)
            residuals: Optional array of residuals to use directly
        
        Returns:
            Numpy array of shape (seq_len,) for residuals
        """
        if residuals is not None:
            # Use provided residuals directly
            return residuals[-seq_len:].astype(np.float32)
        
        # Fallback: create dummy sequence (zeros)
        # In production, this should not be used - residuals should come from history
        logger.warning("Building sequence without residuals - using zeros")
        return np.zeros(seq_len, dtype=np.float32)
    
    def build_from_db_history(
        self,
        timestamp: datetime,
        weather_forecast: Dict[str, float],
        seq_len: int = 168
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Build features using real historical data from database.
        This is the PRIMARY method for Phase 2 production inference.
        
        Args:
            timestamp: Datetime of prediction
            weather_forecast: Dict with keys: temperature, humidity, wind_speed, 
                            cloud_cover, solar_generation
            seq_len: Sequence length (default 168)
        
        Returns:
            Tuple of (xgb_vector, transformer_sequence, metadata)
            - xgb_vector: shape (1, n_features)
            - transformer_sequence: shape (1, seq_len, n_features)
            - metadata: dict with info about data availability
        """
        metadata = {'data_source': 'unknown', 'history_length': 0}
        
        # Get historical data from storage
        if self.storage_service is None:
            logger.warning("No storage service - using fallback features")
            return self.build_for_inference(
                timestamp=timestamp,
                temperature=weather_forecast.get('temperature', 25.0),
                solar_generation=weather_forecast.get('solar_generation', 50.0),
                humidity=weather_forecast.get('humidity'),
                cloud_cover=weather_forecast.get('cloud_cover'),
                seq_len=seq_len
            ) + (metadata,)
        
        try:
            # Fetch last 168 hours of history
            history_df = self.storage_service.get_last_n_hours(seq_len, until_ts=timestamp)
            metadata['history_length'] = len(history_df)
            
            if len(history_df) < 24:
                logger.warning(f"Insufficient history ({len(history_df)}h) - using fallback")
                metadata['data_source'] = 'fallback'
                return self.build_for_inference(
                    timestamp=timestamp,
                    temperature=weather_forecast.get('temperature', 25.0),
                    solar_generation=weather_forecast.get('solar_generation', 50.0),
                    humidity=weather_forecast.get('humidity'),
                    cloud_cover=weather_forecast.get('cloud_cover'),
                    seq_len=seq_len
                ) + (metadata,)
            
            # Pad if needed
            if len(history_df) < seq_len:
                logger.info(f"Padding history from {len(history_df)} to {seq_len} hours")
                history_df = self._pad_history(history_df, seq_len)
            
            metadata['data_source'] = 'database'
            
            # Compute features from history
            features = self._compute_features_from_history(
                timestamp=timestamp,
                history_df=history_df,
                weather_forecast=weather_forecast
            )
            
            # Build XGBoost vector (unscaled)
            xgb_vector = self.build_vector(features).reshape(1, -1)
            
            # For LightGBM+Transformer model, we don't build a sequence here
            # Residuals are computed in the predictor
            transformer_seq = None
            
            return xgb_vector, transformer_seq, metadata
        
        except Exception as e:
            logger.error(f"Error building features from DB: {e}", exc_info=True)
            metadata['data_source'] = 'error_fallback'
            return self.build_for_inference(
                timestamp=timestamp,
                temperature=weather_forecast.get('temperature', 25.0),
                solar_generation=weather_forecast.get('solar_generation', 50.0),
                humidity=weather_forecast.get('humidity'),
                cloud_cover=weather_forecast.get('cloud_cover'),
                seq_len=seq_len
            ) + (metadata,)
    
    def _pad_history(self, history_df: pd.DataFrame, target_len: int) -> pd.DataFrame:
        """Pad history by repeating last available values."""
        if len(history_df) >= target_len:
            return history_df
        
        # Repeat last row to fill
        last_row = history_df.iloc[-1:].copy()
        rows_needed = target_len - len(history_df)
        
        padding = pd.concat([last_row] * rows_needed, ignore_index=True)
        
        # Adjust timestamps
        last_ts = history_df['ts'].iloc[-1]
        for i in range(len(padding)):
            padding.loc[i, 'ts'] = last_ts + timedelta(hours=i+1)
        
        return pd.concat([history_df, padding], ignore_index=True)
    
    def _compute_features_from_history(
        self,
        timestamp: datetime,
        history_df: pd.DataFrame,
        weather_forecast: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute all features using real historical data.
        Updated for LightGBM model with 17 features.
        
        Args:
            timestamp: Prediction timestamp
            history_df: DataFrame with historical data (168 rows)
            weather_forecast: Weather forecast for prediction time
        
        Returns:
            Dictionary of feature name -> value
        """
        features = {}
        
        # Temporal features
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        month = timestamp.month
        
        # Basic temporal features (separate dow and hour for notebook model)
        features['dow'] = day_of_week
        features['hour'] = hour
        features['month'] = month
        features['is_weekend'] = 1 if day_of_week >= 5 else 0
        features['is_holiday'] = 0  # TODO: integrate holiday calendar
        
        # Weather features (from forecast)
        temp = weather_forecast.get('temperature', self.historical_averages.get('temperature', 25.0))
        humidity = weather_forecast.get('humidity', self.historical_averages.get('humidity', 60.0))
        wind_speed = weather_forecast.get('wind_speed', 3.5)
        solar_rad = weather_forecast.get('solar_generation', 50.0)  # Using solar_generation as proxy for shortwave_radiation
        precip = weather_forecast.get('precipitation', 0.0)
        
        features['temperature_2m'] = temp
        features['relativehumidity_2m'] = humidity
        features['wind_speed_10m'] = wind_speed
        features['shortwave_radiation'] = solar_rad
        features['precipitation'] = precip
        
        # Derived weather features
        # Apparent temperature (feels like) - simplified formula
        features['apparent_temperature'] = temp + 0.33 * (humidity / 100.0 * 6.11 * np.exp(5417.7530 * (1/273.16 - 1/(273.15 + temp))) - 10) - 0.70 * wind_speed
        
        # Heat index - simplified formula
        if temp >= 27 and humidity >= 40:
            features['heat_index'] = -8.78469475556 + 1.61139411 * temp + 2.33854883889 * humidity - 0.14611605 * temp * humidity
        else:
            features['heat_index'] = temp
        
        # Extract demand history
        demand_values = history_df['demand'].values
        
        # Lag features (demand)
        # lag_1: 1 hour ago
        # lag_24: 24 hours ago (same hour yesterday)
        # lag_168: 168 hours ago (same hour last week)
        if len(demand_values) >= 1:
            features['lag_1'] = demand_values[-1]
        else:
            features['lag_1'] = self.historical_averages.get('demand', 3000.0)
        
        if len(demand_values) >= 24:
            features['lag_24'] = demand_values[-24]
        else:
            features['lag_24'] = features['lag_1']
        
        if len(demand_values) >= 168:
            features['lag_168'] = demand_values[-168]
        else:
            features['lag_168'] = features['lag_1']
        
        # Rolling mean features
        # roll24: mean of last 24 hours
        # roll168: mean of last 168 hours (7 days)
        if len(demand_values) >= 24:
            features['roll24'] = np.mean(demand_values[-24:])
        else:
            features['roll24'] = np.mean(demand_values) if len(demand_values) > 0 else features['lag_1']
        
        if len(demand_values) >= 168:
            features['roll168'] = np.mean(demand_values[-168:])
        else:
            features['roll168'] = np.mean(demand_values) if len(demand_values) > 0 else features['lag_1']
        
        return features
    
    def build_sequence_for_timestamp(
        self,
        timestamp: datetime,
        weather_forecast: Optional[Dict[str, float]] = None,
        seq_len: int = 168
    ) -> Tuple[np.ndarray, Dict]:
        """
        Build transformer sequence for a given timestamp using DB history.
        This is the RECOMMENDED method for production inference.
        
        Args:
            timestamp: Datetime of prediction (can be string or datetime)
            weather_forecast: Optional weather forecast dict
            seq_len: Sequence length (default 168)
        
        Returns:
            Tuple of (transformer_sequence, metadata)
            - transformer_sequence: shape (1, seq_len, n_features)
            - metadata: dict with data source info
        """
        # Convert string timestamp to datetime if needed
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Use default weather if not provided
        if weather_forecast is None:
            weather_forecast = {
                'temperature': 25.0,
                'solar_generation': 50.0,
                'humidity': 50.0,
                'cloud_cover': 50.0
            }
        
        # Build from DB history
        _, transformer_seq, metadata = self.build_from_db_history(
            timestamp=timestamp,
            weather_forecast=weather_forecast,
            seq_len=seq_len
        )
        
        return transformer_seq, metadata
    
    def build_for_inference(
        self,
        timestamp: datetime,
        temperature: float,
        solar_generation: float,
        humidity: Optional[float] = None,
        cloud_cover: Optional[float] = None,
        seq_len: int = 168
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Build XGBoost vector for inference.
        LEGACY METHOD - use build_from_db_history for production.
        
        Args:
            timestamp: Datetime of prediction
            temperature: Temperature in °C
            solar_generation: Solar generation in MW
            humidity: Humidity percentage (optional)
            cloud_cover: Cloud cover percentage (optional)
            seq_len: Sequence length (unused, kept for compatibility)
        
        Returns:
            Tuple of (xgb_vector, None)
            - xgb_vector: shape (1, n_features)
            - None: transformer sequence not used in new model
        """
        # Build features
        features = self.build_from_raw(
            timestamp=timestamp,
            temperature=temperature,
            solar_generation=solar_generation,
            humidity=humidity,
            cloud_cover=cloud_cover
        )
        
        # Build XGBoost vector (unscaled)
        xgb_vector = self.build_vector(features).reshape(1, -1)
        
        # For LightGBM+Transformer model, residuals are computed in predictor
        return xgb_vector, None
