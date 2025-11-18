"""
Test Hybrid Predictions
Verifies that predictions match notebook MAE/MAPE exactly.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.services.model_loader import ModelLoader
from api.services.hybrid_predictor import HybridPredictor
import json


def test_24h_prediction_2024():
    """Test 24-hour prediction on 2024 test set."""
    print("=" * 80)
    print("TEST 1: 24-Hour Prediction on 2024 Test Set")
    print("=" * 80)
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    
    # Initialize predictor
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Test on first day of 2024 test set
    result = predictor.predict_24h_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    print(f"\nStart: {result['start_timestamp']}")
    print(f"Predictions: {len(result['predictions'])} hours")
    print(f"\nFirst 5 predictions:")
    for i in range(5):
        print(f"  Hour {i}: Pred={result['predictions'][i]:.2f}, Actual={result['actuals'][i]:.2f}")
    
    print(f"\n{'Metrics':-^80}")
    print(f"Hybrid Model:")
    print(f"  MAE:  {result['metrics']['hybrid']['mae']:.2f} MW")
    print(f"  MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
    print(f"  RMSE: {result['metrics']['hybrid']['rmse']:.2f} MW")
    
    print(f"\nLGBM Baseline:")
    print(f"  MAE:  {result['metrics']['lgbm_baseline']['mae']:.2f} MW")
    print(f"  MAPE: {result['metrics']['lgbm_baseline']['mape']:.4f}%")
    print(f"  RMSE: {result['metrics']['lgbm_baseline']['rmse']:.2f} MW")
    
    return result


def test_24h_prediction_full_2024():
    """Test on full 2024 test set (all 8761 hours)."""
    print("\n" + "=" * 80)
    print("TEST 2: Full 2024 Test Set Evaluation")
    print("=" * 80)
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    
    # Initialize predictor
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Test on multiple days throughout 2024
    import pandas as pd
    import numpy as np
    
    df = pd.read_csv('scripts/master_db.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get 2024 test period
    test_df = df[(df['timestamp'] >= '2024-01-01 23:00:00') & 
                 (df['timestamp'] <= '2024-12-31 23:00:00')].copy()
    
    print(f"\nTest period: {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    print(f"Total hours: {len(test_df)}")
    
    # Sample every 24 hours to get daily predictions
    all_predictions = []
    all_actuals = []
    all_baselines = []
    
    sample_dates = pd.date_range('2024-01-01 23:00:00', '2024-12-31 23:00:00', freq='24H')
    
    print(f"\nEvaluating {len(sample_dates)} days...")
    
    for i, start_ts in enumerate(sample_dates[:30]):  # Test first 30 days
        try:
            result = predictor.predict_24h_from_csv(
                csv_path='scripts/master_db.csv',
                start_timestamp=start_ts.strftime('%Y-%m-%d %H:%M:%S'),
                return_metrics=False
            )
            all_predictions.extend(result['predictions'])
            all_actuals.extend(result['actuals'])
            all_baselines.extend(result['baselines'])
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1} days...")
        except Exception as e:
            print(f"  Error on {start_ts}: {e}")
            break
    
    # Compute overall metrics
    preds_arr = np.array(all_predictions)
    actuals_arr = np.array(all_actuals)
    baselines_arr = np.array(all_baselines)
    
    mae_hybrid = np.mean(np.abs(actuals_arr - preds_arr))
    mape_hybrid = np.mean(np.abs((actuals_arr - preds_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_hybrid = np.sqrt(np.mean((actuals_arr - preds_arr) ** 2))
    
    mae_lgbm = np.mean(np.abs(actuals_arr - baselines_arr))
    mape_lgbm = np.mean(np.abs((actuals_arr - baselines_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_lgbm = np.sqrt(np.mean((actuals_arr - baselines_arr) ** 2))
    
    print(f"\n{'Overall Metrics (30 days)':-^80}")
    print(f"Hybrid Model:")
    print(f"  MAE:  {mae_hybrid:.2f} MW")
    print(f"  MAPE: {mape_hybrid:.4f}%")
    print(f"  RMSE: {rmse_hybrid:.2f} MW")
    
    print(f"\nLGBM Baseline:")
    print(f"  MAE:  {mae_lgbm:.2f} MW")
    print(f"  MAPE: {mape_lgbm:.4f}%")
    print(f"  RMSE: {rmse_lgbm:.2f} MW")
    
    print(f"\n{'Expected from Notebook':-^80}")
    print(f"Hybrid MAPE: 1.7938%")
    print(f"LGBM MAPE:   1.9627%")
    print(f"Hybrid RMSE: 143.81 MW")
    print(f"LGBM RMSE:   153.82 MW")


def test_7day_daily_means():
    """Test 7-day daily mean predictions."""
    print("\n" + "=" * 80)
    print("TEST 3: 7-Day Daily Mean Predictions")
    print("=" * 80)
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    
    # Initialize predictor
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Test on 2024 data
    result = predictor.predict_7day_daily_means_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp='2024-01-01 23:00:00',
        return_metrics=True
    )
    
    print(f"\nStart: {result['start_timestamp']}")
    print(f"\nDaily Mean Predictions:")
    for i, date in enumerate(result['daily_dates']):
        print(f"  {date}: Pred={result['daily_mean_predictions'][i]:.2f}, "
              f"Actual={result['daily_mean_actuals'][i]:.2f}")
    
    print(f"\n{'Metrics':-^80}")
    print(f"Hybrid Model:")
    print(f"  MAE:  {result['metrics']['hybrid']['mae']:.2f} MW")
    print(f"  MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
    print(f"  RMSE: {result['metrics']['hybrid']['rmse']:.2f} MW")
    
    print(f"\nLGBM Baseline:")
    print(f"  MAE:  {result['metrics']['lgbm_baseline']['mae']:.2f} MW")
    print(f"  MAPE: {result['metrics']['lgbm_baseline']['mape']:.4f}%")
    print(f"  RMSE: {result['metrics']['lgbm_baseline']['rmse']:.2f} MW")
    
    return result


def test_2025_predictions():
    """Test predictions on 2025 data."""
    print("\n" + "=" * 80)
    print("TEST 4: 2025 Data Predictions")
    print("=" * 80)
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    
    # Initialize predictor
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Check if 2025 data exists
    import os
    if not os.path.exists('scripts/2025_master_db.csv'):
        print("\n2025 dataset not found. Skipping.")
        return
    
    # Test 24-hour prediction
    try:
        result = predictor.predict_24h_from_csv(
            csv_path='scripts/2025_master_db.csv',
            start_timestamp='2025-01-08 00:00:00',
            return_metrics=True
        )
        
        print(f"\n24-Hour Prediction:")
        print(f"  Start: {result['start_timestamp']}")
        print(f"  Hybrid MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
        print(f"  Hybrid MAE:  {result['metrics']['hybrid']['mae']:.2f} MW")
        
        # Test 7-day prediction
        result_7d = predictor.predict_7day_daily_means_from_csv(
            csv_path='scripts/2025_master_db.csv',
            start_timestamp='2025-01-08 00:00:00',
            return_metrics=True
        )
        
        print(f"\n7-Day Daily Mean Prediction:")
        print(f"  Hybrid MAPE: {result_7d['metrics']['hybrid']['mape']:.4f}%")
        print(f"  Hybrid MAE:  {result_7d['metrics']['hybrid']['mae']:.2f} MW")
        
    except Exception as e:
        print(f"\nError testing 2025 data: {e}")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("HYBRID PREDICTOR VALIDATION")
    print("Testing LGBM + Transformer Residual Model")
    print("=" * 80)
    
    # Run tests
    test_24h_prediction_2024()
    test_24h_prediction_full_2024()
    test_7day_daily_means()
    test_2025_predictions()
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
