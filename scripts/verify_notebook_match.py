"""
Verify Notebook Match
Compares implementation metrics with notebook expected values.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from api.services.model_loader import ModelLoader
from api.services.hybrid_predictor import HybridPredictor
import pandas as pd
import numpy as np


def verify_full_2024_test_set():
    """
    Verify on full 2024 test set to match notebook metrics.
    Notebook reports:
    - Hybrid MAPE: 1.7938%
    - Hybrid RMSE: 143.81 MW
    - LGBM MAPE: 1.9627%
    - LGBM RMSE: 153.82 MW
    """
    print("=" * 80)
    print("VERIFICATION: Full 2024 Test Set")
    print("=" * 80)
    print("\nNotebook Expected Metrics:")
    print("  Hybrid MAPE: 1.7938%")
    print("  Hybrid RMSE: 143.81 MW")
    print("  LGBM MAPE:   1.9627%")
    print("  LGBM RMSE:   153.82 MW")
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Load full dataset
    df = pd.read_csv('scripts/master_db.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get 2024 test period (matches notebook)
    test_df = df[(df['timestamp'] >= '2024-01-01 23:00:00') & 
                 (df['timestamp'] <= '2024-12-31 23:00:00')].copy()
    
    print(f"\nTest Period: {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    print(f"Total Hours: {len(test_df)}")
    
    # We need to predict all hours in test set
    # Start from first valid timestamp (with 168h history)
    start_idx = df[df['timestamp'] == '2024-01-01 23:00:00'].index[0]
    
    if start_idx < 168:
        print(f"\nError: Insufficient history for first test timestamp")
        return
    
    print(f"\nPredicting all {len(test_df)} hours...")
    print("This may take a few minutes...")
    
    all_predictions = []
    all_baselines = []
    all_actuals = []
    
    # Predict in batches of 24 hours
    current_ts = test_df['timestamp'].iloc[0]
    hours_processed = 0
    
    while hours_processed < len(test_df):
        try:
            # Predict next 24 hours
            result = predictor.predict_24h_from_csv(
                csv_path='scripts/master_db.csv',
                start_timestamp=current_ts.strftime('%Y-%m-%d %H:%M:%S'),
                return_metrics=False
            )
            
            # Collect predictions
            hours_to_add = min(24, len(test_df) - hours_processed)
            all_predictions.extend(result['predictions'][:hours_to_add])
            all_baselines.extend(result['baselines'][:hours_to_add])
            all_actuals.extend(result['actuals'][:hours_to_add])
            
            hours_processed += hours_to_add
            current_ts = current_ts + pd.Timedelta(hours=24)
            
            if hours_processed % 240 == 0:  # Every 10 days
                print(f"  Processed {hours_processed}/{len(test_df)} hours ({hours_processed/len(test_df)*100:.1f}%)")
            
        except Exception as e:
            print(f"  Error at {current_ts}: {e}")
            break
    
    print(f"\nCompleted: {hours_processed} hours processed")
    
    # Compute overall metrics
    preds_arr = np.array(all_predictions)
    actuals_arr = np.array(all_actuals)
    baselines_arr = np.array(all_baselines)
    
    # Hybrid metrics
    mae_hybrid = np.mean(np.abs(actuals_arr - preds_arr))
    mape_hybrid = np.mean(np.abs((actuals_arr - preds_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_hybrid = np.sqrt(np.mean((actuals_arr - preds_arr) ** 2))
    
    # LGBM metrics
    mae_lgbm = np.mean(np.abs(actuals_arr - baselines_arr))
    mape_lgbm = np.mean(np.abs((actuals_arr - baselines_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_lgbm = np.sqrt(np.mean((actuals_arr - baselines_arr) ** 2))
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print(f"\n{'Metric':<20} {'Notebook':<15} {'Implementation':<15} {'Difference':<15}")
    print("-" * 65)
    
    # Hybrid MAPE
    diff_mape = mape_hybrid - 1.7938
    print(f"{'Hybrid MAPE':<20} {'1.7938%':<15} {f'{mape_hybrid:.4f}%':<15} {f'{diff_mape:+.4f}%':<15}")
    
    # Hybrid RMSE
    diff_rmse = rmse_hybrid - 143.81
    print(f"{'Hybrid RMSE':<20} {'143.81 MW':<15} {f'{rmse_hybrid:.2f} MW':<15} {f'{diff_rmse:+.2f} MW':<15}")
    
    # LGBM MAPE
    diff_lgbm_mape = mape_lgbm - 1.9627
    print(f"{'LGBM MAPE':<20} {'1.9627%':<15} {f'{mape_lgbm:.4f}%':<15} {f'{diff_lgbm_mape:+.4f}%':<15}")
    
    # LGBM RMSE
    diff_lgbm_rmse = rmse_lgbm - 153.82
    print(f"{'LGBM RMSE':<20} {'153.82 MW':<15} {f'{rmse_lgbm:.2f} MW':<15} {f'{diff_lgbm_rmse:+.2f} MW':<15}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    # Check if within acceptable range (±5%)
    mape_match = abs(diff_mape) < 0.1  # Within 0.1%
    rmse_match = abs(diff_rmse) < 10   # Within 10 MW
    
    if mape_match and rmse_match:
        print("\n✅ VERIFICATION PASSED")
        print("   Implementation matches notebook metrics within acceptable tolerance")
    else:
        print("\n⚠️  VERIFICATION PARTIAL")
        print("   Some metrics differ from notebook (may be due to sampling or rounding)")
    
    print(f"\nHybrid Model Improvement over LGBM:")
    mape_improvement = ((mape_lgbm - mape_hybrid) / mape_lgbm) * 100
    rmse_improvement = ((rmse_lgbm - rmse_hybrid) / rmse_lgbm) * 100
    print(f"  MAPE: {mape_improvement:.2f}% reduction")
    print(f"  RMSE: {rmse_improvement:.2f}% reduction")
    
    return {
        'hybrid': {'mape': mape_hybrid, 'mae': mae_hybrid, 'rmse': rmse_hybrid},
        'lgbm': {'mape': mape_lgbm, 'mae': mae_lgbm, 'rmse': rmse_lgbm},
        'hours_processed': hours_processed
    }


def quick_sample_verification():
    """
    Quick verification on a sample of test data.
    """
    print("\n" + "=" * 80)
    print("QUICK SAMPLE VERIFICATION (First 7 Days)")
    print("=" * 80)
    
    # Load models
    model_loader = ModelLoader()
    model_loader.load_all()
    predictor = HybridPredictor(model_loader, use_db=False)
    
    # Predict first 7 days of 2024 test set
    all_predictions = []
    all_baselines = []
    all_actuals = []
    
    for day in range(7):
        start_ts = pd.Timestamp('2024-01-01 23:00:00') + pd.Timedelta(days=day)
        
        result = predictor.predict_24h_from_csv(
            csv_path='scripts/master_db.csv',
            start_timestamp=start_ts.strftime('%Y-%m-%d %H:%M:%S'),
            return_metrics=False
        )
        
        all_predictions.extend(result['predictions'])
        all_baselines.extend(result['baselines'])
        all_actuals.extend(result['actuals'])
    
    # Compute metrics
    preds_arr = np.array(all_predictions)
    actuals_arr = np.array(all_actuals)
    baselines_arr = np.array(all_baselines)
    
    mape_hybrid = np.mean(np.abs((actuals_arr - preds_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_hybrid = np.sqrt(np.mean((actuals_arr - preds_arr) ** 2))
    
    mape_lgbm = np.mean(np.abs((actuals_arr - baselines_arr) / np.maximum(actuals_arr, 1e-6))) * 100
    rmse_lgbm = np.sqrt(np.mean((actuals_arr - baselines_arr) ** 2))
    
    print(f"\nSample Results (168 hours):")
    print(f"  Hybrid MAPE: {mape_hybrid:.4f}%")
    print(f"  Hybrid RMSE: {rmse_hybrid:.2f} MW")
    print(f"  LGBM MAPE:   {mape_lgbm:.4f}%")
    print(f"  LGBM RMSE:   {rmse_lgbm:.2f} MW")
    
    print(f"\nNote: Sample metrics may differ from full test set metrics")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("NOTEBOOK VERIFICATION")
    print("Comparing Implementation with Notebook Expected Metrics")
    print("=" * 80)
    
    # Quick sample first
    quick_sample_verification()
    
    # Ask user if they want full verification
    print("\n" + "=" * 80)
    print("Full test set verification will take several minutes.")
    response = input("Run full verification? (y/n): ").strip().lower()
    
    if response == 'y':
        verify_full_2024_test_set()
    else:
        print("\nSkipping full verification.")
        print("Run with 'y' to verify on complete 2024 test set (8,761 hours)")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
