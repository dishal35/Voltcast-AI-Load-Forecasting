# Voltcast-AI Project Structure

**Last Updated:** November 8, 2025  
**Phase:** 1 Complete (FastAPI Integration)

---

## Directory Structure

```
Voltcast-AI/
├── api/                          # FastAPI Application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic request/response models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── predictions.py        # Prediction endpoints
│   │   └── status.py             # Status/health endpoints
│   └── services/
│       ├── __init__.py
│       ├── feature_builder.py    # Feature engineering (59 features)
│       ├── model_loader.py       # Artifact loading & validation
│       └── predictor.py          # Hybrid prediction logic
│
├── artifacts/                    # Model Artifacts & Metadata
│   ├── models/
│   │   └── manifest.json         # Canonical artifact manifest
│   ├── feature_importance.csv    # XGBoost feature importance
│   ├── feature_order.json        # Feature definitions (59 features)
│   ├── final_report.json         # Training metrics & metadata
│   ├── golden_samples.json       # Test samples for verification
│   ├── residual_stats.pkl        # Residual statistics (mean, std, n)
│   ├── sarimax_daily.pkl         # SARIMAX model (weekly forecasts)
│   ├── transformer_best.keras    # Transformer model
│   ├── transformer_scaler.pkl    # RobustScaler for features
│   ├── verify_run.json           # Verification results
│   └── xgboost_baseline.json     # XGBoost model
│
├── docs/                         # Documentation
│   ├── API_README.md             # Complete API documentation
│   ├── PHASE_1_CTO_REPORT.md     # Phase 1 implementation report
│   ├── PROJECT_STRUCTURE.md      # This file
│   └── README_VERIFICATION.md    # Verification system guide
│
├── scripts/                      # Utility Scripts
│   ├── validate_manifest.py      # Manifest validation
│   └── verify_run.py             # Golden sample verification
│
├── .venv/                        # Python virtual environment
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container definition
├── README.md                     # Main project README
├── req.txt                       # Python dependencies
├── run_api.py                    # Local development server
└── test_api.py                   # API test suite
```

---

## Key Files Description

### API Application

**api/main.py**
- FastAPI application initialization
- Startup validation and model loading
- CORS middleware configuration
- Route registration
- Comprehensive startup diagnostics

**api/services/feature_builder.py**
- Reconstructs 59 engineered features
- Handles temporal, weather, lag, rolling, and derived features
- Applies RobustScaler for transformer input
- Builds XGBoost vectors and transformer sequences

**api/services/model_loader.py**
- Loads all model artifacts from manifest
- Validates artifact existence
- Caches loaded models
- Provides metadata access

**api/services/predictor.py**
- Orchestrates hybrid predictions
- Combines XGBoost baseline + Transformer residual
- Calculates 95% confidence intervals
- Handles single and horizon predictions

**api/models/schemas.py**
- Pydantic models for request/response validation
- Input validation (temperature, solar, humidity, etc.)
- Type safety and automatic API documentation

**api/routes/predictions.py**
- POST /api/v1/predict - Single prediction
- POST /api/v1/predict/horizon - Multi-hour forecast

**api/routes/status.py**
- GET /api/v1/status - Service status & model metadata
- GET /api/v1/health - Health check
- GET / - Root endpoint with API info

### Artifacts

**artifacts/models/manifest.json**
- Canonical source of truth for artifact paths
- Model metadata (name, version, metrics)
- Training configuration
- Feature definitions

**artifacts/transformer_best.keras**
- Transformer model (2 blocks, 8 heads, 128 dims)
- Input: 168-hour sequences (scaled)
- Output: 24-hour residual predictions

**artifacts/xgboost_baseline.json**
- XGBoost model (1000 trees, depth 8)
- Input: 59 features (unscaled)
- Output: Baseline demand prediction

**artifacts/transformer_scaler.pkl**
- RobustScaler for feature normalization
- Applied to transformer input only
- Pickled with sklearn 1.2.2

**artifacts/feature_order.json**
- Ordered list of 59 feature names
- Ensures correct feature alignment
- Used by FeatureBuilder

**artifacts/residual_stats.pkl**
- Test set residual statistics
- Mean: -0.185 MW
- Std: 3.883 MW
- N: 8,569 samples
- Used for confidence interval calculation

**artifacts/golden_samples.json**
- Test samples for verification
- Contains inputs and expected outputs
- Used by verify_run.py

### Scripts

**scripts/verify_run.py**
- Validates predictions against golden samples
- Checks for model drift
- Configurable tolerance (default: 0.5 MW)
- Outputs results to artifacts/verify_run.json

**scripts/validate_manifest.py**
- Validates manifest.json structure
- Checks artifact file existence
- Verifies metadata completeness

### Deployment

**run_api.py**
- Local development server
- Uvicorn with auto-reload
- Runs on http://0.0.0.0:8000

**Dockerfile**
- Python 3.10 slim base
- CPU-optimized TensorFlow
- Health check configured
- Non-root user
- Port 8000 exposed

**docker-compose.yml**
- Single service configuration
- Port mapping (8000:8000)
- Environment variables
- Health check integration

**test_api.py**
- Comprehensive API test suite
- Tests all endpoints
- Validates response formats
- 5/5 tests passing

### Documentation

**docs/PHASE_1_CTO_REPORT.md**
- Complete Phase 1 implementation report
- Architecture details
- Technical decisions
- Testing results
- Production readiness checklist
- Recommendations for CTO

**docs/API_README.md**
- API endpoint documentation
- Request/response examples
- Configuration guide
- Deployment instructions
- Troubleshooting guide

**docs/README_VERIFICATION.md**
- Verification system documentation
- Golden sample methodology
- Usage instructions

**README.md**
- Project overview
- Quick start guide
- Model information
- API usage examples

---

## File Count Summary

- **API Files:** 11 (main app + services + routes + models)
- **Artifacts:** 11 (models + metadata + stats)
- **Documentation:** 4 (comprehensive guides)
- **Scripts:** 2 (verification + validation)
- **Deployment:** 4 (Docker + test + runner)
- **Total:** 32 core files (excluding .venv)

---

## Dependencies (req.txt)

**Core ML:**
- numpy, pandas, scikit-learn
- xgboost, tensorflow, tf-keras
- matplotlib, seaborn
- statsmodels

**API:**
- fastapi, uvicorn, pydantic
- requests (for testing)

**Optional:**
- redis (for caching)

---

## Removed Files (Cleanup)

The following files were removed as they were one-time setup scripts or superseded by the CTO report:

- `test_predictions.csv` - Old test output
- `scripts/temp/` - One-time setup scripts directory
  - `compute_residual_stats.py`
  - `create_golden_samples.py`
  - `extract_golden_from_test.py`
  - `verification_results.json`
  - `verification_script.py`
  - `verify_artifacts.py`
- `scripts/feature_order.py` - One-time feature extraction
- `scripts/feature_engineer.py` - One-time feature engineering
- `docs/CHECKLIST.md` - Phase 1 complete
- `docs/PHASE_0_STATUS.md` - Superseded by CTO report
- `docs/VERIFICATION_COMPLETE.md` - Superseded by CTO report
- `docs/ORGANIZATION_SUMMARY.md` - Consolidated into CTO report

---

## Next Phase Structure

**Phase 2 (Dashboard Integration) will add:**
- `dashboard/` - Dashboard application
- `data/` - Historical data storage
- `config/` - Configuration files
- Additional API endpoints for dashboard
- Real-time data ingestion pipeline

---

**Status:** Clean and organized for CTO review  
**Phase 1:** ✅ Complete  
**Phase 2:** Ready to begin
