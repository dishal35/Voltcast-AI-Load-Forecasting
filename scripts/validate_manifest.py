#!/usr/bin/env python3
# validate_manifest.py
"""
Validates that all paths in manifest.json exist and are accessible.
"""
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent  # Go up to project root
manifest_path = BASE / "artifacts" / "models" / "manifest.json"

if not manifest_path.exists():
    print(f"ERROR: Manifest not found at {manifest_path}")
    sys.exit(1)

print(f"Validating manifest: {manifest_path}")
print("=" * 60)

with open(manifest_path) as f:
    manifest = json.load(f)

errors = []
warnings = []

def check_path(path_str, description, required=True):
    """Check if a path exists"""
    if path_str is None:
        if required:
            errors.append(f"Missing required path: {description}")
        else:
            warnings.append(f"Optional path not set: {description}")
        return
    
    path = BASE / path_str
    if path.exists():
        print(f"✓ {description}: {path_str}")
    else:
        if required:
            errors.append(f"Missing file: {description} at {path_str}")
        else:
            warnings.append(f"Optional file missing: {description} at {path_str}")

# Check hourly model
print("\nHourly Model:")
hourly = manifest.get("models", {}).get("hourly", {})
check_path(hourly.get("transformer_path"), "Transformer model")
check_path(hourly.get("baseline_path"), "XGBoost baseline")
check_path(hourly.get("scaler_path"), "Feature scaler")
check_path(hourly.get("residual_scaler_path"), "Residual scaler", required=False)
check_path(hourly.get("feature_order_path"), "Feature order")
check_path(hourly.get("residual_stats_path"), "Residual stats", required=False)
check_path(hourly.get("metrics_path"), "Metrics report")

# Check weekly model
print("\nWeekly Model:")
weekly = manifest.get("models", {}).get("weekly", {})
check_path(weekly.get("path"), "SARIMAX model")

# Check verification
print("\nVerification:")
verification = manifest.get("verification", {})
check_path(verification.get("golden_samples_path"), "Golden samples", required=False)
verify_script = verification.get("verify_script")
if verify_script:
    check_path(verify_script, "Verify script")

# Check residuals_by_horizon
print("\nResidual Statistics:")
check_path(manifest.get("residuals_by_horizon_path"), "Residuals by horizon (pkl)", required=False)
check_path(manifest.get("residuals_by_horizon_json_path"), "Residuals by horizon (json)", required=False)

# Check metadata
print("\nMetadata:")
if "model_store_version" in manifest:
    print(f"✓ Model store version: {manifest['model_store_version']}")
else:
    warnings.append("Missing model_store_version")

if "generated_at" in manifest:
    print(f"✓ Generated at: {manifest['generated_at']}")
else:
    warnings.append("Missing generated_at timestamp")

# Check database config
print("\nDatabase Configuration:")
db_config = manifest.get("database", {})
if db_config:
    print(f"✓ Database type: {db_config.get('type', 'not specified')}")
    print(f"✓ Database path: {db_config.get('path', 'not specified')}")
else:
    warnings.append("Missing database configuration")

# Check weather config
print("\nWeather Configuration:")
weather_config = manifest.get("weather", {})
if weather_config:
    print(f"✓ Weather provider: {weather_config.get('provider', 'not specified')}")
    print(f"✓ Coordinates: {weather_config.get('coords', 'not specified')}")
else:
    warnings.append("Missing weather configuration")

# Check performance metrics
print("\nPerformance Metrics:")
metrics = hourly.get("performance_metrics", {})
if metrics:
    baseline = metrics.get("baseline", {})
    hybrid = metrics.get("hybrid", {})
    
    if baseline.get("mae"):
        print(f"✓ Baseline MAE: {baseline['mae']:.4f}")
    if hybrid.get("mae"):
        print(f"✓ Hybrid MAE: {hybrid['mae']:.4f}")
else:
    warnings.append("Missing performance metrics")

# Summary
print("\n" + "=" * 60)
print(f"Validation Summary:")
print(f"  Errors:   {len(errors)}")
print(f"  Warnings: {len(warnings)}")

if errors:
    print("\nERRORS:")
    for err in errors:
        print(f"  ✗ {err}")

if warnings:
    print("\nWARNINGS:")
    for warn in warnings:
        print(f"  ⚠ {warn}")

if errors:
    print("\n✗ VALIDATION FAILED")
    sys.exit(1)
else:
    print("\n✓ VALIDATION PASSED")
    if warnings:
        print("  (with warnings)")
    sys.exit(0)
