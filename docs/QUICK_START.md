# Voltcast-AI Quick Start Guide

**Phase 1 Complete** - FastAPI Integration ✅

---

## 🚀 Start the API (30 seconds)

### Option 1: Local Development
```bash
# Activate virtual environment
.venv\Scripts\activate

# Start server
python run_api.py

# API available at http://localhost:8000
```

### Option 2: Docker
```bash
# Build and run
docker-compose up --build

# API available at http://localhost:8000
```

---

## 🧪 Test the API

### Run Test Suite
```bash
python test_api.py
```

**Expected:** 5/5 tests passing ✅

### Manual Test
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Make prediction
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2023-01-07T15:00:00",
    "temperature": 25.5,
    "solar_generation": 150.0,
    "humidity": 65.0,
    "cloud_cover": 30.0
  }'
```

---

## 📚 Documentation

- **API Docs:** http://localhost:8000/docs (interactive)
- **ReDoc:** http://localhost:8000/redoc (alternative)
- **Full API Guide:** `docs/API_README.md`
- **CTO Report:** `docs/PHASE_1_CTO_REPORT.md`
- **Project Structure:** `docs/PROJECT_STRUCTURE.md`

---

## 🔍 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/predict` | POST | Single prediction with CI |
| `/api/v1/predict/horizon` | POST | Multi-hour forecast (1-168h) |
| `/api/v1/status` | GET | Model metadata & stats |
| `/api/v1/health` | GET | Health check |
| `/` | GET | API information |
| `/docs` | GET | Interactive docs |

---

## 📊 Model Information

- **Architecture:** Hybrid Transformer + XGBoost
- **Features:** 59 engineered features
- **Sequence Length:** 168 hours (1 week)
- **Forecast Horizon:** 24 hours
- **Test MAE:** 2.016 MW
- **Test RMSE:** 3.888 MW
- **Confidence Interval:** ±7.61 MW (95% CI)

---

## 🛠️ Verification

```bash
# Verify against golden samples
python scripts/verify_run.py

# Validate manifest
python scripts/validate_manifest.py
```

---

## 📁 Key Files

- `api/main.py` - FastAPI application
- `api/services/feature_builder.py` - Feature engineering
- `api/services/predictor.py` - Prediction logic
- `artifacts/models/manifest.json` - Model metadata
- `test_api.py` - Test suite
- `run_api.py` - Development server

---

## ⚡ Quick Commands

```bash
# Install dependencies
pip install -r req.txt

# Start API
python run_api.py

# Run tests
python test_api.py

# Verify models
python scripts/verify_run.py

# Docker build
docker-compose up --build

# Stop API (if running in background)
# Press Ctrl+C in terminal
```

---

## 🎯 What's Working

✅ All API endpoints functional  
✅ Feature engineering (59 features)  
✅ Hybrid predictions (XGBoost + Transformer)  
✅ Confidence intervals (95% CI)  
✅ Request validation (Pydantic)  
✅ Error handling  
✅ Health checks  
✅ Docker deployment  
✅ Interactive documentation  
✅ Test suite (5/5 passing)  

---

## ⚠️ Known Limitations

- Lag features use placeholders (need historical data pipeline)
- No authentication (add before production)
- No rate limiting (add before production)
- Scaler version warning (sklearn 1.2.2 → 1.4.2)

**Note:** These are documented and will be addressed in Phase 2 or production hardening.

---

## 🔄 Next Steps

1. **CTO Review** - Review `docs/PHASE_1_CTO_REPORT.md`
2. **Phase 2 Planning** - Dashboard + Historical Data
3. **Production Prep** - Authentication, rate limiting, monitoring

---

## 💡 Tips

- API auto-reloads on code changes (development mode)
- Check logs for detailed startup diagnostics
- Use `/docs` for interactive API testing
- Confidence intervals based on test set residuals
- All predictions include baseline + residual components

---

## 🆘 Troubleshooting

**API won't start:**
- Check if port 8000 is available
- Verify all artifacts exist in `artifacts/`
- Check Python version (3.10+)

**Tests failing:**
- Ensure API is running
- Check network connectivity to localhost:8000
- Review test output for specific errors

**Prediction errors:**
- Validate input ranges (temp: -50 to 60°C, etc.)
- Check request format matches schema
- Review API logs for details

---

**Status:** Production-ready with documented limitations  
**Last Updated:** November 8, 2025  
**Phase:** 1 Complete ✅
