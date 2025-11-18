"""
Verify predictions against expected values for January 8, 2025.
Tests that the API produces predictions matching the notebook outputs.
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from api.services.model_loader import ModelLoader
from api.services.predictor import HybridPredictor
from datetime import datetime
import numpy as np
import pandas as pd

# Expected values from your data
EXPECTED_DATA = [
    {"timestamp": "2025-01-08 00:00:00", "load": 2386.29, "baseline_pred": 4792.435, "hybrid_pred": 4772.903},
    {"timestamp": "2025-01-08 01:00:00", "load": 2069.198, "baseline_pred": 2037.764, "hybrid_pred": 2029.424},
    {"timestamp": "2025-01-08 02:00:00", "load": 1907.174, "baseline_pred": 1935.027, "hybrid_pred": 1897.298},
    {"timestamp": "2025-01-08 03:00:00", "load": 1838.369, "baseline_pred": 1851.512, "hybrid_pred": 1860.928},
    {"timestamp": "2025-01-08 04:00:00", "load": 1924.063, "baseline_pred": 1911.314, "hybrid_pred": 1944.97},
    {"timestamp": "2025-01-08 05:00:00", "load": 2319.341, "baseline_pred": 2333.944, "hybrid_pred": 2427.165},
    {"timestamp": "2025-01-08 06:00:00", "load": 3214.718, "baseline_pred": 3232.695, "hybrid_pred": 3243.125},
    {"timestamp": "2025-01-08 07:00:00", "load": 4192.523, "baseline_pred": 4061.194, "hybrid_pred": 4090.262},
    {"timestamp": "2025-01-08 08:00:00", "load": 4760.962, "baseline_pred": 4639.445, "hybrid_pred": 4689.648},
    {"timestamp": "2025-01-08 09:00:00", "load": 5143.272, "baseline_pred": 5039.717, "hybrid_pred": 5067.57},
]

def calculate_metrics(actual, predicted):
    """Calculate RMSE and MAE."""
    actual = np.array(actual)
    predicted = np.array(predicted)
    
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    mae = np.mean(np.abs(actual - predicted))
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    
    return rmse, mae, mape

def main():
    print("="*70)
    print("PREDICTION VERIFICATION - January 8, 2025")
    print("="*70)
    
    # Load models
    print("\n1. Loading models...")
    loader = ModelLoader()
    loader.load_all()
    print("   Models loaded successfully")
    
    # Initialize predictor
    print("\n2. Initializing predictor...")
    predictor = HybridPredictor(loader, use_db=True)
    print("   Predictor initialized")
    
    # Make predictions
    print("\n3. Making predictions for first 10 hours of 2025-01-08...")
    print("-"*70)
    
    actual_loads = []
    expected_baselines = []
    expected_hybrids = []
    predicted_baselines = []
    predicted_hybrids = []
    
    for i, expected in enumerate(EXPECTED_DATA):
        timestamp = datetime.fromisoformat(expected["timestamp"])
        
        try:
            result = predictor.predict(
                timestamp=timestamp,
                return_components=True
            )
            
            pred_baseline = result['components']['baseline']
            pred_hybrid = result['prediction']
            
            actual_loads.append(expected['load'])
            expected_baselines.append(expected['baseline_pred'])
            expected_hybrids.append(expected['hybrid_pred'])
            predicted_baselines.append(pred_baseline)
            predicted_hybrids.append(pred_hybrid)
            
            # Calculate errors
            baseline_error = abs(pred_baseline - expected['baseline_pred'])
            hybrid_error = abs(pred_hybrid - expected['hybrid_pred'])
            
            status_baseline = "[OK]" if baseline_error < 10 else "[DIFF]"
            status_hybrid = "[OK]" if hybrid_error < 10 else "[DIFF]"
            
            hour_str = timestamp.strftime('%H:00')
            print(f"\nHour {i} ({hour_str})")
            print(f"  Actual Load:       {expected['load']:8.2f} MW")
            print(f"  Expected Baseline: {expected['baseline_pred']:8.2f} MW")
            print(f"  Predicted Baseline: {pred_baseline:8.2f} MW  {status_baseline} (error: {baseline_error:.2f})")
            print(f"  Expected Hybrid:   {expected['hybrid_pred']:8.2f} MW")
            print(f"  Predicted Hybrid:  {pred_hybrid:8.2f} MW  {status_hybrid} (error: {hybrid_error:.2f})")
            
        except Exception as e:
            hour_str = timestamp.strftime('%H:00')
            print(f"\n[FAILED] Hour {i} ({hour_str}): {e}")
            continue
    
    # Calculate overall metrics
    print("\n" + "="*70)
    print("OVERALL METRICS")
    print("="*70)
    
    # Baseline metrics
    baseline_rmse, baseline_mae, baseline_mape = calculate_metrics(
        expected_baselines, predicted_baselines
    )
    print("\nBaseline Predictions:")
    print(f"  RMSE: {baseline_rmse:.2f} MW")
    print(f"  MAE:  {baseline_mae:.2f} MW")
    print(f"  MAPE: {baseline_mape:.2f}%")
    
    # Hybrid metrics
    hybrid_rmse, hybrid_mae, hybrid_mape = calculate_metrics(
        expected_hybrids, predicted_hybrids
    )
    print("\nHybrid Predictions:")
    print(f"  RMSE: {hybrid_rmse:.2f} MW")
    print(f"  MAE:  {hybrid_mae:.2f} MW")
    print(f"  MAPE: {hybrid_mape:.2f}%")
    
    # Hybrid vs Actual
    actual_rmse, actual_mae, actual_mape = calculate_metrics(
        actual_loads, predicted_hybrids
    )
    print("\nHybrid vs Actual Load:")
    print(f"  RMSE: {actual_rmse:.2f} MW")
    print(f"  MAE:  {actual_mae:.2f} MW")
    print(f"  MAPE: {actual_mape:.2f}%")
    
    # Pass/Fail criteria
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)
    
    tolerance = 50.0  # MW tolerance
    
    if baseline_rmse < tolerance and hybrid_rmse < tolerance:
        print(f"\n[PASS] Predictions match expected values (RMSE < {tolerance} MW)")
        return True
    else:
        print(f"\n[FAIL] Predictions differ from expected values (RMSE >= {tolerance} MW)")
        print(f"\nPossible reasons:")
        print(f"  - Database may not have historical data for 2025-01-08")
        print(f"  - Model artifacts may be different from notebook")
        print(f"  - Feature computation may differ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
