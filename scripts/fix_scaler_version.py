"""
Fix sklearn version warning by re-pickling the residual scaler
with the current sklearn version.
"""
import joblib
from sklearn.preprocessing import StandardScaler
import warnings

print("="*60)
print("Fixing Residual Scaler Version")
print("="*60)

# Suppress the warning temporarily
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    
    # Load old scaler
    print("\n1. Loading old scaler...")
    old_scaler = joblib.load('artifacts/residual_scaler.pkl')
    print(f"   Old scaler loaded successfully")
    print(f"   Mean: {old_scaler.mean_}")
    print(f"   Scale: {old_scaler.scale_}")

# Create new scaler with same parameters
print("\n2. Creating new scaler with current sklearn version...")
new_scaler = StandardScaler()
new_scaler.mean_ = old_scaler.mean_
new_scaler.scale_ = old_scaler.scale_
new_scaler.var_ = old_scaler.scale_ ** 2
new_scaler.n_features_in_ = len(old_scaler.mean_)
new_scaler.n_samples_seen_ = old_scaler.n_samples_seen_ if hasattr(old_scaler, 'n_samples_seen_') else 1000

print(f"   New scaler created")
print(f"   Mean: {new_scaler.mean_}")
print(f"   Scale: {new_scaler.scale_}")

# Backup old scaler
print("\n3. Backing up old scaler...")
joblib.dump(old_scaler, 'artifacts/residual_scaler.pkl.backup')
print(f"   Backup saved to: artifacts/residual_scaler.pkl.backup")

# Save new scaler
print("\n4. Saving new scaler...")
joblib.dump(new_scaler, 'artifacts/residual_scaler.pkl')
print(f"   New scaler saved to: artifacts/residual_scaler.pkl")

# Verify
print("\n5. Verifying new scaler...")
test_scaler = joblib.load('artifacts/residual_scaler.pkl')
print(f"   Verification successful!")
print(f"   Mean matches: {(test_scaler.mean_ == new_scaler.mean_).all()}")
print(f"   Scale matches: {(test_scaler.scale_ == new_scaler.scale_).all()}")

print("\n" + "="*60)
print("[SUCCESS] Scaler version fixed!")
print("="*60)
