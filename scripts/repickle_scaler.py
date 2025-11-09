"""
Re-pickle transformer_scaler.pkl in current environment to remove sklearn version warning.
Task #4 from Phase 2 CTO review.
"""
import joblib
import sys
from pathlib import Path

scaler_path = Path('artifacts/transformer_scaler.pkl')
backup_path = Path('artifacts/transformer_scaler.pkl.backup')

print("Re-pickling transformer scaler...")
print(f"Current sklearn version: {joblib.__version__}")

# Load old scaler
try:
    scaler = joblib.load(scaler_path)
    print(f"✓ Loaded scaler")
    print(f"  Type: {type(scaler).__name__}")
    print(f"  n_features_in_: {scaler.n_features_in_}")
except Exception as e:
    print(f"✗ Failed to load scaler: {e}")
    sys.exit(1)

# Backup original
try:
    import shutil
    shutil.copy(scaler_path, backup_path)
    print(f"✓ Backed up original to {backup_path}")
except Exception as e:
    print(f"WARNING: Could not create backup: {e}")

# Re-pickle with current environment
try:
    joblib.dump(scaler, scaler_path)
    print(f"✓ Re-pickled scaler to {scaler_path}")
except Exception as e:
    print(f"✗ Failed to re-pickle: {e}")
    sys.exit(1)

# Verify
try:
    scaler_test = joblib.load(scaler_path)
    assert scaler_test.n_features_in_ == scaler.n_features_in_
    print(f"✓ Verified: n_features_in_ = {scaler_test.n_features_in_}")
    print("\n✓ SUCCESS: Scaler re-pickled successfully")
except Exception as e:
    print(f"✗ Verification failed: {e}")
    sys.exit(1)
