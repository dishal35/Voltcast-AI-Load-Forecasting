"""
Diagnose why API is slow - test each component separately.
"""
import time
from datetime import datetime, timedelta

print("="*60)
print("API PERFORMANCE DIAGNOSIS")
print("="*60)

# Test 1: Model Loading
print("\n1. Testing Model Loading...")
start = time.time()
try:
    from api.services.model_loader import ModelLoader
    loader = ModelLoader()
    loader.load_all()
    elapsed = time.time() - start
    print(f"   ✅ Models loaded in {elapsed:.2f}s")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

# Test 2: CSV Loading
print("\n2. Testing CSV Loading...")
start = time.time()
try:
    import pandas as pd
    df = pd.read_csv('scripts/2025_master_db.csv', parse_dates=['timestamp'])
    elapsed = time.time() - start
    print(f"   ✅ CSV loaded in {elapsed:.2f}s ({len(df)} rows)")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

# Test 3: Hybrid Predictor Initialization
print("\n3. Testing Hybrid Predictor...")
start = time.time()
try:
    from api.services.hybrid_predictor import HybridPredictor
    predictor = HybridPredictor(loader, use_db=False)
    elapsed = time.time() - start
    print(f"   ✅ Predictor initialized in {elapsed:.2f}s")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

# Test 4: Simple CSV Prediction
print("\n4. Testing CSV-based 24h Prediction...")
start = time.time()
try:
    result = predictor.predict_24h_from_csv(
        csv_path='scripts/2025_master_db.csv',
        start_timestamp='2025-11-16 00:00:00',
        return_metrics=False
    )
    elapsed = time.time() - start
    print(f"   ✅ Prediction completed in {elapsed:.2f}s")
    print(f"      First prediction: {result['predictions'][0]:.2f} MW")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

# Test 5: Iterative Prediction (1 hour only)
print("\n5. Testing Iterative Prediction (1 hour)...")
start = time.time()
try:
    from api.services.iterative_predictor import predict_future_iterative
    
    # Get last 168 hours
    history_df = df.tail(168).reset_index()
    history_df = history_df[['timestamp', 'load']]
    
    # Predict just 1 hour
    result = predict_future_iterative(
        start_timestamp=datetime(2025, 11, 18, 0, 0),
        horizon=1,
        history_df=history_df,
        lgbm_model=predictor.lgbm_model,
        transformer_model=predictor.transformer_model,
        residual_scaler=predictor.residual_scaler,
        feature_order=predictor.feature_order,
        weather_forecasts=[{
            'temperature': 20.0,
            'humidity': 60.0,
            'wind_speed': 3.5,
            'solar_radiation': 50.0,
            'precipitation': 0.0
        }]
    )
    elapsed = time.time() - start
    print(f"   ✅ 1-hour prediction in {elapsed:.2f}s")
    print(f"      Prediction: {result['predictions'][0]:.2f} MW")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

# Test 6: Iterative Prediction (24 hours)
print("\n6. Testing Iterative Prediction (24 hours)...")
start = time.time()
try:
    result = predict_future_iterative(
        start_timestamp=datetime(2025, 11, 18, 0, 0),
        horizon=24,
        history_df=history_df,
        lgbm_model=predictor.lgbm_model,
        transformer_model=predictor.transformer_model,
        residual_scaler=predictor.residual_scaler,
        feature_order=predictor.feature_order,
        weather_forecasts=[{
            'temperature': 20.0,
            'humidity': 60.0,
            'wind_speed': 3.5,
            'solar_radiation': 50.0,
            'precipitation': 0.0
        }] * 24
    )
    elapsed = time.time() - start
    print(f"   ✅ 24-hour prediction in {elapsed:.2f}s")
    print(f"      Average: {sum(result['predictions'])/24:.2f} MW")
except Exception as e:
    elapsed = time.time() - start
    print(f"   ❌ Failed after {elapsed:.2f}s: {e}")

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)
