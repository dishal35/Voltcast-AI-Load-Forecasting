#!/usr/bin/env python3
# verify_run.py
"""
Verification script that compares current model predictions against golden samples.
Returns exit code 0 on success, non-zero on failure.
Writes detailed results to artifacts/verify_run.json
"""
import json
import joblib
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent  # Go up to project root
ART = BASE / "artifacts"

# Add project root to Python path for imports
sys.path.insert(0, str(BASE))

# Tolerance from environment or default
TOL = float(os.getenv("GOLDEN_TOL_ABS", "0.5"))  # MW

print(f"Voltcast-AI Load Forecasting - Artifact Verification")
print(f"=" * 60)
print(f"Tolerance: ±{TOL} MW")
print(f"Timestamp: {datetime.utcnow().isoformat()}")
print()

# Load golden samples
golden_path = ART / "golden_samples.json"
if not golden_path.exists():
    print(f"ERROR: Missing {golden_path}")
    sys.exit(1)

with open(golden_path) as f:
    golden_data = json.load(f)

samples = golden_data.get("samples", golden_data)
if not samples:
    print("ERROR: No samples found in golden_samples.json")
    sys.exit(1)

print(f"Loaded {len(samples)} golden samples\n")

# Load artifacts
try:
    import xgboost as xgb
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(ART / "xgboost_baseline.json"))
    print("✓ Loaded XGBoost model")
except Exception as e:
    print(f"ERROR loading XGBoost: {e}")
    sys.exit(1)

try:
    with open(ART / "feature_order.json") as f:
        feat_data = json.load(f)
        feature_order = feat_data.get("feature_order", feat_data) if isinstance(feat_data, dict) else feat_data
    print(f"✓ Loaded feature order ({len(feature_order)} features)")
except Exception as e:
    print(f"ERROR loading feature_order.json: {e}")
    sys.exit(1)

# Load scaler (optional)
scaler = None
scaler_path = ART / "transformer_scaler.pkl"
if scaler_path.exists():
    try:
        scaler = joblib.load(str(scaler_path))
        print("✓ Loaded scaler")
    except Exception as e:
        print(f"WARNING: Failed to load scaler: {e}")

# Load transformer (optional)
tf_model = None
tf_model_path = ART / "transformer_best.keras"
if tf_model_path.exists():
    try:
        from tf_keras.models import load_model
        tf_model = load_model(str(tf_model_path))
        print(f"✓ Loaded transformer model (input shape: {tf_model.input_shape})")
    except Exception as e:
        print(f"WARNING: Failed to load transformer: {e}")
        print("  Will only verify baseline predictions")

print()

# Initialize storage service and feature builder
from api.services.storage import StorageService
from api.services.feature_builder import FeatureBuilder

storage_service = StorageService()
feature_builder = FeatureBuilder(
    feature_order=feature_order,
    scaler=scaler,
    storage_service=storage_service
)
print("✓ Initialized storage service and feature builder\n")

def build_feature_vector(sample, storage_service, feature_builder):
    """Build feature vector - use pre-computed if available, otherwise reconstruct"""
    
    # Check if sample has pre-computed feature vector
    if 'feature_vector' in sample:
        # Use the actual training features!
        vec = np.array(sample['feature_vector'], dtype=float)
        return vec.reshape(1, -1)
    
    # Fallback: try to reconstruct (for backwards compatibility)
    from datetime import datetime
    
    # Parse timestamp
    ts_str = sample.get('ts_iso') or sample.get('timestamp')
    ts = datetime.fromisoformat(ts_str.replace(' ', 'T')) if isinstance(ts_str, str) else ts_str
    
    # Weather forecast from sample
    weather_forecast = {
        'temperature': sample.get('temperature', 25.0),
        'solar_generation': sample.get('solar_generation', 50.0),
        'humidity': sample.get('humidity', 50.0),
        'cloud_cover': sample.get('cloud_cover', 50.0)
    }
    
    # Build features using DB history
    try:
        xgb_vec, _, metadata = feature_builder.build_from_db_history(
            timestamp=ts,
            weather_forecast=weather_forecast,
            seq_len=168
        )
        return xgb_vec.astype(float)
    except Exception as e:
        logger.warning(f"Failed to build from DB history: {e}, using fallback")
        # Fallback to simple feature building
        features = feature_builder.build_from_raw(
            timestamp=ts,
            temperature=weather_forecast['temperature'],
            solar_generation=weather_forecast['solar_generation'],
            humidity=weather_forecast.get('humidity'),
            cloud_cover=weather_forecast.get('cloud_cover')
        )
        vec = feature_builder.build_vector(features)
        return vec.reshape(1, -1).astype(float)

def build_transformer_seq(sample, seq_len=168):
    """Build transformer sequence"""
    n_features = len(feature_order)
    base_vec = np.zeros((n_features,), dtype=float)
    
    for idx, fname in enumerate(feature_order):
        if fname in sample:
            base_vec[idx] = float(sample[fname])
    
    if scaler is not None:
        try:
            base_vec = scaler.transform(base_vec.reshape(1, -1)).reshape(-1)
        except:
            pass
    
    seq = np.tile(base_vec, (seq_len, 1)).astype(np.float32)
    return np.expand_dims(seq, axis=0)

# Verify each sample
results = []
errors = []
passed = 0
failed = 0

for idx, sample_data in enumerate(samples):
    # Handle different golden sample formats
    if "input" in sample_data and "expected" in sample_data:
        sample = sample_data["input"]
        expected = sample_data["expected"]
        tolerance = sample_data.get("tolerance", {}).get("absolute", TOL)
    else:
        # Old format compatibility
        sample = sample_data.get("sample", sample_data)
        expected = {
            "baseline_first": sample_data.get("baseline_first"),
            "residual_first": sample_data.get("residual_first"),
            "hybrid_first": sample_data.get("hybrid_first")
        }
        tolerance = TOL
    
    sample_id = sample.get("timestamp", sample.get("ts_iso", f"sample_{idx}"))
    print(f"[{idx+1}/{len(samples)}] {sample_id}")
    
    # Predict baseline
    try:
        vec = build_feature_vector(sample, storage_service, feature_builder)
        cur_baseline = float(xgb_model.predict(vec)[0])
    except Exception as e:
        print(f"  ERROR: Baseline prediction failed: {e}")
        errors.append({"sample": sample_id, "error": str(e)})
        failed += 1
        continue
    
    # Predict residual (if transformer available)
    cur_resid = None
    if tf_model is not None and expected.get("residual_first") is not None:
        try:
            seq_len = tf_model.input_shape[1] if len(tf_model.input_shape) > 1 else 168
            seq = build_transformer_seq(sample, seq_len=seq_len)
            pred = tf_model.predict(seq, verbose=0)
            cur_resid = float(np.array(pred).reshape(-1)[0])
        except Exception as e:
            print(f"  WARNING: Transformer prediction failed: {e}")
    
    # Compute hybrid
    cur_hybrid = cur_baseline + (cur_resid if cur_resid is not None else 0.0)
    
    # Compare with expected
    exp_baseline = expected.get("baseline_first")
    exp_resid = expected.get("residual_first")
    exp_hybrid = expected.get("hybrid_first")
    
    baseline_err = abs(cur_baseline - exp_baseline) if exp_baseline is not None else None
    resid_err = abs(cur_resid - exp_resid) if (cur_resid is not None and exp_resid is not None) else None
    hybrid_err = abs(cur_hybrid - exp_hybrid) if exp_hybrid is not None else None
    
    # Check tolerance
    baseline_ok = baseline_err is None or baseline_err <= tolerance
    hybrid_ok = hybrid_err is None or hybrid_err <= tolerance
    sample_ok = baseline_ok and hybrid_ok
    
    if sample_ok:
        passed += 1
        status = "✓ PASS"
    else:
        failed += 1
        status = "✗ FAIL"
    
    print(f"  {status}")
    print(f"    Baseline: {cur_baseline:.4f} (expected: {exp_baseline:.4f}, error: {baseline_err:.4f})")
    if cur_resid is not None:
        print(f"    Residual: {cur_resid:.4f} (expected: {exp_resid:.4f}, error: {resid_err:.4f})")
    print(f"    Hybrid:   {cur_hybrid:.4f} (expected: {exp_hybrid:.4f}, error: {hybrid_err:.4f})")
    
    results.append({
        "sample": sample_id,
        "ok": sample_ok,
        "current": {
            "baseline_first": cur_baseline,
            "residual_first": cur_resid,
            "hybrid_first": cur_hybrid
        },
        "expected": expected,
        "errors": {
            "baseline": baseline_err,
            "residual": resid_err,
            "hybrid": hybrid_err
        },
        "tolerance": tolerance
    })

# Write results
output = {
    "generated_at": datetime.utcnow().isoformat(),
    "tolerance": TOL,
    "summary": {
        "total": len(samples),
        "passed": passed,
        "failed": failed
    },
    "results": results
}

output_path = ART / "verify_run.json"
with open(output_path, "w", encoding="utf8") as f:
    json.dump(output, f, indent=2)

print()
print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {len(samples)}")
print(f"Wrote detailed results to {output_path}")

if failed > 0:
    print("\n✗ VERIFICATION FAILED")
    sys.exit(2)
else:
    print("\n✓ VERIFICATION PASSED")
    sys.exit(0)
