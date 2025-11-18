"""
Diagnose prediction differences - step by step comparison with notebook
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
from datetime import datetime
import lightgbm as lgb
import torch
import joblib

# Expected values from notebook
EXPECTED = {
    "timestamp": "2025-01-08 00:00:00",
    "load": 2386.29,
    "baseline_pred": 4792.435,
    "hybrid_pred": 4772.903
}

print("="*70)
print("DIAGNOSTIC: Matching Notebook Predictions")
print("="*70)

# 1. Load models directly
print("\n1. Loading models...")
lgbm_model = lgb.Booster(model_file='artifacts/lgbm_model.txt')
print(f"   LightGBM loaded: {lgbm_model.num_trees()} trees")

from api.services.model_loader import ResidualTransformer
transformer = ResidualTransformer()
transformer.load_state_dict(torch.load('artifacts/transformer_residual.pt', map_location='cpu'))
transformer.eval()
print(f"   Transformer loaded")

residual_scaler = joblib.load('artifacts/residual_scaler.pkl')
print(f"   Residual scaler loaded: mean={residual_scaler.mean_[0]:.2f}, std={residual_scaler.scale_[0]:.2f}")

# 2. Load data
print("\n2. Loading data...")
df = pd.read_csv('scripts/2025_master_db.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Get the specific row
target_ts = pd.Timestamp("2025-01-08 00:00:00")
matching = df[df['timestamp'] == target_ts]
if len(matching) == 0:
    print(f"   ✗ No data found for {target_ts}")
    print(f"   Available range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    sys.exit(1)
row = matching.iloc[0]
print(f"   Found row for {target_ts}")
print(f"   Actual load: {row['load']:.2f}")

# 3. Extract features in exact order
print("\n3. Building features...")
feature_order = [
    'temperature_2m', 'relativehumidity_2m', 'apparent_temperature',
    'shortwave_radiation', 'precipitation', 'wind_speed_10m',
    'is_holiday', 'dow', 'hour', 'is_weekend', 'month', 'heat_index',
    'lag_1', 'lag_24', 'lag_168', 'roll24', 'roll168'
]

features = []
for feat in feature_order:
    val = row[feat]
    features.append(val)
    print(f"   {feat:25s} = {val}")

features_array = np.array(features).reshape(1, -1)
print(f"\n   Feature array shape: {features_array.shape}")

# 4. Get baseline prediction
print("\n4. LightGBM Baseline Prediction...")
baseline_pred = lgbm_model.predict(features_array)[0]
print(f"   Predicted: {baseline_pred:.3f}")
print(f"   Expected:  {EXPECTED['baseline_pred']:.3f}")
print(f"   Difference: {abs(baseline_pred - EXPECTED['baseline_pred']):.3f}")

if abs(baseline_pred - EXPECTED['baseline_pred']) < 1.0:
    print("   ✓ BASELINE MATCHES!")
else:
    print("   ✗ BASELINE DIFFERS")

# 5. Get historical residuals for transformer
print("\n5. Computing Historical Residuals...")
# Get 168 hours before target
idx = df[df['timestamp'] == target_ts].index[0]
if idx < 168:
    print(f"   ✗ Not enough history (need 168, have {idx})")
    sys.exit(1)

history = df.iloc[idx-168:idx].copy()
print(f"   History: {len(history)} rows from {history['timestamp'].min()} to {history['timestamp'].max()}")

# Compute baseline predictions for history
hist_features = []
for i in range(len(history)):
    hist_row = history.iloc[i]
    hist_feat = [hist_row[f] for f in feature_order]
    hist_features.append(hist_feat)

hist_features_array = np.array(hist_features)
hist_baselines = lgbm_model.predict(hist_features_array)
print(f"   Historical baselines computed: {len(hist_baselines)} values")

# Compute residuals
hist_actuals = history['load'].values
hist_residuals = hist_actuals - hist_baselines
print(f"   Residuals: mean={hist_residuals.mean():.2f}, std={hist_residuals.std():.2f}")

# Scale residuals
hist_residuals_scaled = residual_scaler.transform(hist_residuals.reshape(-1, 1)).flatten()
print(f"   Scaled residuals: mean={hist_residuals_scaled.mean():.4f}, std={hist_residuals_scaled.std():.4f}")

# 6. Transformer prediction
print("\n6. Transformer Residual Prediction...")
seq_tensor = torch.tensor(hist_residuals_scaled, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
print(f"   Input shape: {seq_tensor.shape}")

with torch.no_grad():
    residual_scaled = transformer(seq_tensor).item()

print(f"   Scaled residual: {residual_scaled:.4f}")

# Unscale
residual_pred = residual_scaler.inverse_transform([[residual_scaled]])[0][0]
print(f"   Unscaled residual: {residual_pred:.3f}")

# 7. Hybrid prediction
print("\n7. Hybrid Prediction...")
hybrid_pred = baseline_pred + residual_pred
print(f"   Hybrid = Baseline + Residual")
print(f"   Hybrid = {baseline_pred:.3f} + {residual_pred:.3f}")
print(f"   Hybrid = {hybrid_pred:.3f}")
print(f"   Expected: {EXPECTED['hybrid_pred']:.3f}")
print(f"   Difference: {abs(hybrid_pred - EXPECTED['hybrid_pred']):.3f}")

if abs(hybrid_pred - EXPECTED['hybrid_pred']) < 1.0:
    print("   ✓ HYBRID MATCHES!")
else:
    print("   ✗ HYBRID DIFFERS")

# 8. Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Actual Load:      {row['load']:.2f} MW")
print(f"Baseline:         {baseline_pred:.2f} MW (expected: {EXPECTED['baseline_pred']:.2f})")
print(f"Residual:         {residual_pred:.2f} MW")
print(f"Hybrid:           {hybrid_pred:.2f} MW (expected: {EXPECTED['hybrid_pred']:.2f})")
print()
print(f"Baseline Error:   {abs(baseline_pred - EXPECTED['baseline_pred']):.2f} MW")
print(f"Hybrid Error:     {abs(hybrid_pred - EXPECTED['hybrid_pred']):.2f} MW")

if abs(baseline_pred - EXPECTED['baseline_pred']) < 1.0 and abs(hybrid_pred - EXPECTED['hybrid_pred']) < 1.0:
    print("\n✓ SUCCESS: Predictions match notebook!")
else:
    print("\n✗ FAIL: Predictions differ from notebook")
    print("\nPossible issues:")
    print("  1. Feature order mismatch")
    print("  2. Different model file")
    print("  3. Different residual computation")
    print("  4. Different transformer weights")
