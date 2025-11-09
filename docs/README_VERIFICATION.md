# Voltcast-AI Load Forecasting - Verification Setup

## 🎯 Current Status: Ready for test_prediction.csv

All verification infrastructure is complete and tested. We need **test_prediction.csv** to finalize golden samples and residual statistics.

## 📦 What's Been Created

### Core Scripts
- ✅ **compute_residual_stats.py** - Extracts residual statistics
- ✅ **create_golden_samples.py** - Generates golden samples by running models
- ✅ **extract_golden_from_test.py** - Extracts golden samples from test CSV (RECOMMENDED)
- ✅ **verify_run.py** - Main verification script with exit codes
- ✅ **validate_manifest.py** - Validates manifest integrity

### Artifacts
- ✅ **artifacts/models/manifest.json** - Canonical model manifest (validated ✓)
- ⏳ **artifacts/residual_stats.pkl** - Waiting for test_prediction.csv
- ⏳ **artifacts/golden_samples.json** - Needs expected outputs added

### Documentation
- ✅ **VERIFICATION_SETUP.md** - Detailed setup guide
- ✅ **PHASE_0_STATUS.md** - Phase 0 status and decisions
- ✅ **README_VERIFICATION.md** - This file

## 🚀 Quick Start (Once test_prediction.csv is provided)

### Step 1: Place test_prediction.csv
```bash
# Place file in project root: D:\Voltcast-AI Load Forecasting\test_prediction.csv
```

### Step 2: Extract Golden Samples (RECOMMENDED)
```bash
python extract_golden_from_test.py
```
This extracts actual training outputs for the 3 golden sample timestamps.

### Step 3: Compute Residual Stats
```bash
python compute_residual_stats.py
```
Creates `artifacts/residual_stats.pkl` with mean/std/n.

### Step 4: Run Verification
```bash
python verify_run.py
```
Compares current predictions vs golden samples. Exit code 0 = pass.

### Step 5: Check Results
```bash
cat artifacts/verify_run.json
```

## 📋 test_prediction.csv Format

Required columns (any of these names work):
- **Timestamp**: `timestamp`, `datetime`, `date`, `time`
- **Actual**: `actual`, `y_true`, `true`, `demand`
- **Baseline**: `xgboost`, `baseline`, `xgb`, `base`
- **Hybrid** (optional): `hybrid`, `final`, `prediction`

Example:
```csv
timestamp,actual,xgboost,hybrid
2016-12-03 15:00:00,391.38,394.70,394.72
2022-10-28 14:00:00,598.39,595.20,595.18
2020-09-01 09:00:00,442.99,440.50,440.48
```

## 🎯 Golden Sample Timestamps

The verification looks for these 3 timestamps:
1. `2016-12-03T15:00:00` (Saturday afternoon, low temp, high solar)
2. `2022-10-28T14:00:00` (Friday afternoon, high temp, low solar)
3. `2020-09-01T09:00:00` (Tuesday morning, very high temp, medium solar)

If exact matches aren't found, the script uses the first 3 rows.

## ✅ Manifest Validation Results

```
✓ Transformer model: artifacts/transformer_best.keras
✓ XGBoost baseline: artifacts/xgboost_baseline.json
✓ Feature scaler: artifacts/transformer_scaler.pkl
✓ Feature order: artifacts/feature_order.json (59 features)
✓ SARIMAX model: artifacts/sarimax_daily.pkl
✓ Metrics report: artifacts/final_report.json
✓ Baseline MAE: 2.0155 MW
✓ Hybrid MAE: 2.0156 MW
```

## 🔧 Configuration

### Tolerance
**Default: 0.5 MW absolute**

Change via environment variable:
```bash
set GOLDEN_TOL_ABS=0.25
python verify_run.py
```

### Residual Scaler
**Status: NOT NEEDED**

The training script did not scale residuals:
- Residuals computed as: `y_train - xgb_train_pred`
- Fed directly to transformer
- Transformer outputs raw residuals
- Hybrid = baseline + residual (no inverse transform)

Manifest confirms: `"residuals_scaled": false`

## 📊 Verification Flow

```
test_prediction.csv
    ↓
extract_golden_from_test.py
    ↓
artifacts/golden_samples.json (with expected outputs)
    +
artifacts/residual_stats.pkl
    ↓
verify_run.py
    ↓
artifacts/verify_run.json
    ↓
Exit 0 (pass) or 2 (fail)
```

## 🐛 Troubleshooting

### "Cannot find residual stats"
- Ensure test_prediction.csv is in project root
- Check it has `actual` and `xgboost` columns
- Run: `python compute_residual_stats.py`

### "No timestamp matches found"
- Script will use first 3 rows as fallback
- Check timestamp format in test_prediction.csv
- Ensure dates are parseable by pandas

### "Transformer prediction failed"
- Ensure TensorFlow 2.16.2 and tf-keras 2.16.0 installed
- Check: `python -c "from tf_keras.models import load_model; print('OK')"`
- If fails, run inside Docker with TensorFlow

### "Verification failed - tolerance exceeded"
- Check artifacts/verify_run.json for details
- May need to adjust tolerance
- Verify feature_order.json matches training

## 📝 Manager Decisions

### Decision 1: Tolerance
- [x] **Approved: 0.5 MW** (strict but allows floating-point differences)
- [ ] Change to: _____ MW

### Decision 2: Residual Stats Source
- [x] **Approved: Test set residuals** (from test_prediction.csv)
- [ ] Change to: _____

## 🎓 Technical Notes

### Why No residual_scaler.pkl?
Your training code:
```python
train_residuals = y_train - xgb_train_pred
# No scaling applied to residuals
generator = ResidualGenerator(..., y=train_residuals)  # Raw residuals
```

The transformer learned to predict raw residuals directly. No inverse transform needed.

### Feature Engineering
59 features in exact order:
- Temporal: hour_cos, hour_sin, doy_cos, doy_sin, dow_cos, dow_sin, month_cos, month_sin
- Weather: temperature, humidity, cloud_cover, heat_index, temp_solar_interaction
- Demand lags: 1, 2, 3, 6, 12, 24, 48, 72, 168 hours
- Rolling stats: mean, std, q25, q75 over 6, 12, 24, 168 hour windows
- Differences: 1h, 24h, 2nd order
- FFT components: 1, 2, 3 (168-hour period)
- Flags: is_weekend, is_holiday, days_to/since_holiday

### Model Architecture
- Sequence length: 168 hours (1 week)
- Horizon: 24 hours
- Transformer: 2 blocks, 8 heads, 128 dims
- XGBoost: 1000 trees, depth 8

## 📞 Next Steps

1. **Provide test_prediction.csv**
2. **Run the 4 commands above**
3. **Verify exit code 0**
4. **Commit all artifacts**

Then we can move to FastAPI integration!

## 🔗 Related Files

- `artifacts/models/manifest.json` - Model metadata
- `artifacts/final_report.json` - Training metrics
- `artifacts/feature_order.json` - Feature definitions
- `PHASE_0_STATUS.md` - Detailed status
- `VERIFICATION_SETUP.md` - Setup guide
