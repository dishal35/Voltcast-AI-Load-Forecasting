# Voltcast-AI Load Forecasting

Hybrid transformer-XGBoost model for electricity demand forecasting.

## Project Structure

```
├── artifacts/              # Model artifacts and outputs
│   ├── models/            # Model manifest
│   ├── *.keras            # Trained models
│   ├── *.pkl              # Scalers and stats
│   └── *.json             # Metadata and results
├── scripts/               # Active scripts
│   ├── verify_run.py      # Main verification script
│   ├── validate_manifest.py  # Manifest validator
│   ├── feature_engineer.py   # Feature engineering
│   └── temp/              # One-time setup scripts
├── docs/                  # Documentation
│   ├── README_VERIFICATION.md  # Verification guide
│   ├── VERIFICATION_COMPLETE.md  # Phase 0 summary
│   └── *.md               # Other documentation
└── req.txt                # Python dependencies
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r req.txt
```

### 2. Verify Artifacts
```bash
python scripts/verify_run.py
```

### 3. Validate Manifest
```bash
python scripts/validate_manifest.py
```

## Model Information

**Architecture**: Hybrid Transformer + XGBoost
- **Baseline**: XGBoost (1000 trees, depth 8)
- **Residual Correction**: Transformer (2 blocks, 8 heads, 128 dims)
- **Sequence Length**: 168 hours (1 week)
- **Forecast Horizon**: 24 hours

**Performance** (Test Set):
- Baseline MAE: 2.015 MW
- Hybrid MAE: 2.016 MW
- RMSE: 3.888 MW

**Features**: 59 engineered features
- Temporal: hour/day/month cyclical encoding
- Weather: temperature, humidity, solar generation
- Demand lags: 1, 2, 3, 6, 12, 24, 48, 72, 168 hours
- Rolling statistics: mean, std, quantiles
- FFT components

## Artifacts

All trained models and metadata are in `artifacts/`:
- `transformer_best.keras` - Transformer model
- `xgboost_baseline.json` - XGBoost model
- `transformer_scaler.pkl` - Feature scaler (RobustScaler)
- `sarimax_daily.pkl` - SARIMAX model (weekly forecasts)
- `feature_order.json` - Feature definitions (59 features)
- `golden_samples.json` - Test samples for verification
- `residual_stats.pkl` - Residual statistics
- `final_report.json` - Training metrics
- `models/manifest.json` - Canonical manifest

## Verification

The verification system ensures model artifacts are valid and predictions are reproducible.

**Run verification:**
```bash
python scripts/verify_run.py
```

**Set tolerance** (default 0.5 MW):
```bash
set GOLDEN_TOL_ABS=0.25
python scripts/verify_run.py
```

**Check results:**
```bash
cat artifacts/verify_run.json
```

See `docs/README_VERIFICATION.md` for details.

## Documentation

**📋 Start Here:** [docs/INDEX.md](docs/INDEX.md) - Complete documentation index

**Key Documents:**
- `docs/PHASE_1_CTO_REPORT.md` - ⭐ Complete Phase 1 implementation report (CTO review)
- `docs/QUICK_START.md` - 🚀 Get API running in 30 seconds
- `docs/API_README.md` - 📚 Complete API documentation
- `docs/PROJECT_STRUCTURE.md` - 📁 Project organization
- `docs/README_VERIFICATION.md` - 🔍 Verification system guide

## Key Technical Notes

### No Residual Scaler
The transformer predicts **raw residuals** (not scaled):
```python
train_residuals = y_train - xgb_train_pred  # Raw residuals
# No scaling applied before training
hybrid_prediction = baseline + residual  # Direct addition
```

### Residual Statistics
From test set (8,569 samples):
- Mean: -0.185 MW (nearly zero)
- Std: 3.883 MW
- Residuals are very small (~0.004 MW average)

### Dependencies
- Python 3.10+
- TensorFlow 2.16.2
- tf-keras 2.16.0
- XGBoost 2.0+
- scikit-learn 1.4+

**Note**: Scaler was pickled with sklearn 1.2.2, running with 1.4.2 may show warnings.

## Development

### One-Time Setup Scripts
Located in `scripts/temp/` (already executed):
- `compute_residual_stats.py` - Computed residual statistics
- `extract_golden_from_test.py` - Extracted golden samples
- `create_golden_samples.py` - Alternative golden sample generator
- `verify_artifacts.py` - Initial artifact verification

These scripts were used during Phase 0 setup and are kept for reference.

## API Usage

### Start the API Server
```bash
# Local development
python run_api.py

# Docker deployment
docker-compose up --build
```

### Make Predictions
```bash
# Single prediction
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2023-01-07T15:00:00",
    "temperature": 25.5,
    "solar_generation": 150.0,
    "humidity": 65.0,
    "cloud_cover": 30.0
  }'

# 24-hour forecast
curl -X POST http://localhost:8000/api/v1/predict/horizon \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2023-01-07T15:00:00",
    "temperature": 25.5,
    "solar_generation": 150.0,
    "horizon": 24
  }'
```

### API Documentation
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Status: http://localhost:8000/api/v1/status
- Full API docs: `docs/API_README.md`

## Testing

### Run API Tests
```bash
python test_api.py
```

### Run Verification
```bash
python scripts/verify_run.py
```

## Next Steps

1. ✅ Phase 0: Verification infrastructure (COMPLETE)
2. ✅ Phase 1: FastAPI integration (COMPLETE)
3. 📊 Phase 2: Dashboard integration
4. 🚀 Phase 3: Deployment

## License

[Your License]

## Contact

[Your Contact Info]
