"""
Hybrid Predictor Service
Implements LGBM + Transformer Residual predictions exactly as in notebook.
Supports:
1. 24-hour day-ahead predictions
2. 7-day daily mean predictions
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import torch

from .model_loader import ModelLoader
from .storage import get_storage_service

logger = logging.getLogger(__name__)


class HybridPredictor:
    """
    Hybrid predictor using LightGBM baseline + Transformer residual correction.
    Matches notebook implementation for exact MAE/MAPE reproduction.
    """
    
    def __init__(self, model_loader: ModelLoader, use_db: bool = True):
        """
        Initialize hybrid predictor.
        
        Args:
            model_loader: Loaded ModelLoader instance
            use_db: Whether to use database for historical data
        """
        self.model_loader = model_loader
        self.use_db = use_db
        
        # Get models
        self.lgbm_model = model_loader.get_model('lgbm')
        self.transformer_model = model_loader.get_model('transformer')
        
        # Get scalers
        self.residual_scaler = model_loader.get_scaler('residual')
        
        # Get feature order
        self.feature_order = model_loader.get_metadata('feature_order')
        
        # Get residual stats
        self.residual_stats = model_loader.get_metadata('residual_stats') or {
            'mean': 9.11, 'std': 89.52
        }
        
        # Storage service
        self.storage_service = get_storage_service() if use_db else None
        
        # Sequence length for transformer
        self.seq_len = 168  # 7 days of hourly residuals
        
        logger.info(f"HybridPredictor initialized (DB mode: {use_db})")
        logger.info(f"Feature order: {len(self.feature_order)} features")
        logger.info(f"Residual stats: mean={self.residual_stats['mean']:.2f}, std={self.residual_stats['std']:.2f}")
    
    def _load_data_from_csv(self, csv_path: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load data from CSV file for a specific date range.
        
        Args:
            csv_path: Path to CSV file
            start_date: Start date (YYYY-MM-DD HH:MM:SS)
            end_date: End date (YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame with data in the specified range
        """
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        return df[mask].copy()
    
    def _build_feature_vector(self, row: pd.Series) -> np.ndarray:
        """
        Build feature vector from a data row matching the exact feature order.
        
        Args:
            row: Pandas Series with all required features
        
        Returns:
            Feature vector as numpy array
        """
        vector = np.zeros(len(self.feature_order), dtype=np.float32)
        
        for i, feat_name in enumerate(self.feature_order):
            if feat_name in row.index:
                vector[i] = row[feat_name]
            else:
                logger.warning(f"Feature {feat_name} not found in row, using 0.0")
                vector[i] = 0.0
        
        return vector
    
    def _compute_residuals_from_data(
        self, 
        df: pd.DataFrame,
        start_idx: int,
        end_idx: int
    ) -> np.ndarray:
        """
        Compute historical residuals from data.
        
        Args:
            df: DataFrame with features and actual load
            start_idx: Start index in dataframe
            end_idx: End index in dataframe
        
        Returns:
            Array of scaled residuals
        """
        # Build feature vectors for historical period
        feature_vectors = []
        for idx in range(start_idx, end_idx):
            feat_vec = self._build_feature_vector(df.iloc[idx])
            feature_vectors.append(feat_vec)
        
        feature_array = np.array(feature_vectors)
        
        # Get LGBM predictions
        lgbm_preds = self.lgbm_model.predict(feature_array)
        
        # Get actual values
        actuals = df.iloc[start_idx:end_idx]['load'].values
        
        # Compute residuals
        residuals = actuals - lgbm_preds
        
        # Scale residuals
        if self.residual_scaler is not None:
            residuals_scaled = self.residual_scaler.transform(residuals.reshape(-1, 1)).flatten()
            return residuals_scaled
        else:
            return residuals
    
    def predict_24h_from_csv(
        self,
        csv_path: str,
        start_timestamp: str,
        return_metrics: bool = True
    ) -> Dict:
        """
        Predict 24 hours starting from start_timestamp using data from CSV.
        This matches the notebook's prediction methodology exactly.
        
        Args:
            csv_path: Path to CSV file (master_db.csv or 2025_master_db.csv)
            start_timestamp: Start timestamp (YYYY-MM-DD HH:MM:SS)
            return_metrics: Whether to compute MAE/MAPE if actuals available
        
        Returns:
            Dictionary with predictions, actuals, and metrics
        """
        logger.info(f"Predicting 24h from {start_timestamp} using {csv_path}")
        
        # Load full dataset
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Find start index
        start_ts = pd.to_datetime(start_timestamp)
        start_idx = df[df['timestamp'] == start_ts].index
        
        if len(start_idx) == 0:
            raise ValueError(f"Timestamp {start_timestamp} not found in {csv_path}")
        
        start_idx = start_idx[0]
        
        # Check if we have enough history (168 hours before start)
        if start_idx < self.seq_len:
            raise ValueError(f"Insufficient history: need {self.seq_len} hours before {start_timestamp}")
        
        # Check if we have 24 hours of data to predict
        if start_idx + 24 > len(df):
            raise ValueError(f"Insufficient data: need 24 hours after {start_timestamp}")
        
        # Compute historical residuals (168 hours before prediction start)
        hist_start = start_idx - self.seq_len
        hist_end = start_idx
        historical_residuals = self._compute_residuals_from_data(df, hist_start, hist_end)
        
        logger.info(f"Computed {len(historical_residuals)} historical residuals")
        
        # Predict 24 hours
        predictions = []
        baselines = []
        residuals = []
        actuals = []
        timestamps = []
        
        # Current residual sequence (will be updated as we predict)
        current_residuals = historical_residuals.copy()
        
        for h in range(24):
            pred_idx = start_idx + h
            pred_row = df.iloc[pred_idx]
            timestamps.append(pred_row['timestamp'])
            
            # Build feature vector
            feat_vec = self._build_feature_vector(pred_row)
            
            # LGBM baseline prediction
            baseline = self.lgbm_model.predict(feat_vec.reshape(1, -1))[0]
            baselines.append(float(baseline))
            
            # Transformer residual prediction
            if self.transformer_model is not None and len(current_residuals) >= self.seq_len:
                # Use last 168 residuals
                residual_seq = current_residuals[-self.seq_len:]
                
                # Prepare tensor: [batch=1, seq_len=168, features=1]
                seq_tensor = torch.tensor(residual_seq, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
                
                with torch.no_grad():
                    residual_scaled = self.transformer_model(seq_tensor).item()
                
                # Unscale residual
                if self.residual_scaler is not None:
                    residual = self.residual_scaler.inverse_transform([[residual_scaled]])[0][0]
                else:
                    residual = residual_scaled
                
                residuals.append(float(residual))
                
                # Update residual sequence for next prediction
                # Append the scaled residual (for next iteration)
                current_residuals = np.append(current_residuals[1:], residual_scaled)
            else:
                residuals.append(0.0)
            
            # Hybrid prediction
            hybrid = baseline + residuals[-1]
            predictions.append(max(0.0, float(hybrid)))
            
            # Get actual value
            actuals.append(float(pred_row['load']))
        
        # Compute metrics
        metrics = {}
        if return_metrics and len(actuals) > 0:
            actuals_arr = np.array(actuals)
            preds_arr = np.array(predictions)
            baselines_arr = np.array(baselines)
            
            # MAE
            mae_hybrid = np.mean(np.abs(actuals_arr - preds_arr))
            mae_lgbm = np.mean(np.abs(actuals_arr - baselines_arr))
            
            # MAPE
            mape_hybrid = np.mean(np.abs((actuals_arr - preds_arr) / np.maximum(actuals_arr, 1e-6))) * 100
            mape_lgbm = np.mean(np.abs((actuals_arr - baselines_arr) / np.maximum(actuals_arr, 1e-6))) * 100
            
            # RMSE
            rmse_hybrid = np.sqrt(np.mean((actuals_arr - preds_arr) ** 2))
            rmse_lgbm = np.sqrt(np.mean((actuals_arr - baselines_arr) ** 2))
            
            metrics = {
                'hybrid': {
                    'mae': float(mae_hybrid),
                    'mape': float(mape_hybrid),
                    'rmse': float(rmse_hybrid)
                },
                'lgbm_baseline': {
                    'mae': float(mae_lgbm),
                    'mape': float(mape_lgbm),
                    'rmse': float(rmse_lgbm)
                }
            }
            
            logger.info(f"Hybrid MAPE: {mape_hybrid:.4f}%, MAE: {mae_hybrid:.2f}, RMSE: {rmse_hybrid:.2f}")
            logger.info(f"LGBM MAPE: {mape_lgbm:.4f}%, MAE: {mae_lgbm:.2f}, RMSE: {rmse_lgbm:.2f}")
        
        return {
            'start_timestamp': start_timestamp,
            'timestamps': [ts.isoformat() for ts in timestamps],
            'predictions': predictions,
            'baselines': baselines,
            'residuals': residuals,
            'actuals': actuals,
            'metrics': metrics
        }
    
    def predict_7day_daily_means_from_csv(
        self,
        csv_path: str,
        start_timestamp: str,
        return_metrics: bool = True
    ) -> Dict:
        """
        Predict daily mean load for next 7 days using data from CSV.
        
        Args:
            csv_path: Path to CSV file
            start_timestamp: Start timestamp (YYYY-MM-DD HH:MM:SS)
            return_metrics: Whether to compute MAE/MAPE if actuals available
        
        Returns:
            Dictionary with daily mean predictions and metrics
        """
        logger.info(f"Predicting 7-day daily means from {start_timestamp} using {csv_path}")
        
        # Load full dataset
        df = pd.read_csv(csv_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Find start index
        start_ts = pd.to_datetime(start_timestamp)
        start_idx = df[df['timestamp'] == start_ts].index
        
        if len(start_idx) == 0:
            raise ValueError(f"Timestamp {start_timestamp} not found in {csv_path}")
        
        start_idx = start_idx[0]
        
        # Check if we have enough history
        if start_idx < self.seq_len:
            raise ValueError(f"Insufficient history: need {self.seq_len} hours before {start_timestamp}")
        
        # Check if we have 7 days (168 hours) of data to predict
        if start_idx + 168 > len(df):
            raise ValueError(f"Insufficient data: need 168 hours after {start_timestamp}")
        
        # Compute historical residuals
        hist_start = start_idx - self.seq_len
        hist_end = start_idx
        historical_residuals = self._compute_residuals_from_data(df, hist_start, hist_end)
        
        # Predict 168 hours (7 days)
        hourly_predictions = []
        hourly_baselines = []
        hourly_actuals = []
        
        current_residuals = historical_residuals.copy()
        
        for h in range(168):
            pred_idx = start_idx + h
            pred_row = df.iloc[pred_idx]
            
            # Build feature vector
            feat_vec = self._build_feature_vector(pred_row)
            
            # LGBM baseline
            baseline = self.lgbm_model.predict(feat_vec.reshape(1, -1))[0]
            hourly_baselines.append(float(baseline))
            
            # Transformer residual
            if self.transformer_model is not None and len(current_residuals) >= self.seq_len:
                residual_seq = current_residuals[-self.seq_len:]
                seq_tensor = torch.tensor(residual_seq, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
                
                with torch.no_grad():
                    residual_scaled = self.transformer_model(seq_tensor).item()
                
                if self.residual_scaler is not None:
                    residual = self.residual_scaler.inverse_transform([[residual_scaled]])[0][0]
                else:
                    residual = residual_scaled
                
                current_residuals = np.append(current_residuals[1:], residual_scaled)
            else:
                residual = 0.0
            
            # Hybrid prediction
            hybrid = baseline + residual
            hourly_predictions.append(max(0.0, float(hybrid)))
            
            # Actual
            hourly_actuals.append(float(pred_row['load']))
        
        # Compute daily means
        hourly_preds_arr = np.array(hourly_predictions).reshape(7, 24)
        hourly_baselines_arr = np.array(hourly_baselines).reshape(7, 24)
        hourly_actuals_arr = np.array(hourly_actuals).reshape(7, 24)
        
        daily_predictions = hourly_preds_arr.mean(axis=1).tolist()
        daily_baselines = hourly_baselines_arr.mean(axis=1).tolist()
        daily_actuals = hourly_actuals_arr.mean(axis=1).tolist()
        
        # Generate daily timestamps
        daily_timestamps = []
        for day in range(7):
            day_ts = start_ts + timedelta(days=day)
            daily_timestamps.append(day_ts.date().isoformat())
        
        # Compute metrics
        metrics = {}
        if return_metrics:
            daily_preds_arr = np.array(daily_predictions)
            daily_actuals_arr = np.array(daily_actuals)
            daily_baselines_arr = np.array(daily_baselines)
            
            # MAE
            mae_hybrid = np.mean(np.abs(daily_actuals_arr - daily_preds_arr))
            mae_lgbm = np.mean(np.abs(daily_actuals_arr - daily_baselines_arr))
            
            # MAPE
            mape_hybrid = np.mean(np.abs((daily_actuals_arr - daily_preds_arr) / np.maximum(daily_actuals_arr, 1e-6))) * 100
            mape_lgbm = np.mean(np.abs((daily_actuals_arr - daily_baselines_arr) / np.maximum(daily_actuals_arr, 1e-6))) * 100
            
            # RMSE
            rmse_hybrid = np.sqrt(np.mean((daily_actuals_arr - daily_preds_arr) ** 2))
            rmse_lgbm = np.sqrt(np.mean((daily_actuals_arr - daily_baselines_arr) ** 2))
            
            metrics = {
                'hybrid': {
                    'mae': float(mae_hybrid),
                    'mape': float(mape_hybrid),
                    'rmse': float(rmse_hybrid)
                },
                'lgbm_baseline': {
                    'mae': float(mae_lgbm),
                    'mape': float(mape_lgbm),
                    'rmse': float(rmse_lgbm)
                }
            }
            
            logger.info(f"Daily Mean Hybrid MAPE: {mape_hybrid:.4f}%, MAE: {mae_hybrid:.2f}")
            logger.info(f"Daily Mean LGBM MAPE: {mape_lgbm:.4f}%, MAE: {mae_lgbm:.2f}")
        
        return {
            'start_timestamp': start_timestamp,
            'daily_dates': daily_timestamps,
            'daily_mean_predictions': daily_predictions,
            'daily_mean_baselines': daily_baselines,
            'daily_mean_actuals': daily_actuals,
            'hourly_predictions': hourly_predictions,
            'hourly_actuals': hourly_actuals,
            'metrics': metrics
        }
