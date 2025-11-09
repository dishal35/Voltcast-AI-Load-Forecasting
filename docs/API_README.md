# Voltcast-AI FastAPI Documentation

## Overview

FastAPI service for hybrid transformer-XGBoost electricity demand forecasting.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Feature Builder │    │  Model Loader   │
│                 │    │                  │    │                 │
│ • Routes        │───▶│ • Raw → Features │───▶│ • XGBoost       │
│ • Validation    │    │ • Scaling        │    │ • Transformer   │
│ • Error Handling│    │ • Sequencing     │    │ • Scalers       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Hybrid Predictor│    │   Pydantic      │    │   Artifacts     │
│                 │    │   Models        │    │                 │
│ • Baseline      │    │                  │    │ • manifest.json │
│ • Residual      │    │ • Request/       │    │ • *.keras       │
│ • Confidence    │    │   Response       │    │ • *.pkl         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## API Endpoints

### Core Endpoints

#### `POST /api/v1/predict`
Single point prediction with confidence intervals.

**Request:**
```json
{
  "timestamp": "2023-01-07T15:00:00",
  "temperature": 25.5,
  "solar_generation": 150.0,
  "humidity": 65.0,
  "cloud_cover": 30.0
}
```

**Response:**
```json
{
  "timestamp": "2023-01-07T15:00:00",
  "prediction": 487.23,
  "confidence_interval": {
    "lower": 479.62,
    "upper": 494.84,
    "margin": 7.61
  },
  "components": {
    "baseline": 487.15,
    "residual": 0.08
  }
}
```

#### `POST /api/v1/predict/horizon`
Multi-hour forecast (up to 168 hours).

**Request:**
```json
{
  "timestamp": "2023-01-07T15:00:00",
  "temperature": 25.5,
  "solar_generation": 150.0,
  "humidity": 65.0,
  "cloud_cover": 30.0,
  "horizon": 24
}
```

**Response:**
```json
{
  "timestamp": "2023-01-07T15:00:00",
  "horizon": 24,
  "predictions": [487.23, 485.67, 483.12, ...],
  "baseline": 487.15,
  "residuals": [0.08, -1.48, -4.03, ...],
  "confidence_interval": {
    "margin": 7.61,
    "note": "Apply ±margin to each prediction for 95% CI"
  }
}
```

### Status Endpoints

#### `GET /api/v1/status`
Service status and model metadata.

**Response:**
```json
{
  "status": "operational",
  "version": "1.0",
  "artifacts": {
    "transformer": true,
    "xgboost": true,
    "scaler": true,
    "feature_order": true,
    "residual_stats": true
  },
  "model_info": {
    "name": "hybrid_transformer_xgboost",
    "seq_len": 168,
    "horizon": 24,
    "n_features": 59,
    "training_date": "2025-11-07T20:44:29.901404",
    "metrics": {
      "mae": 2.016,
      "rmse": 3.888,
      "mape": 0.413
    }
  },
  "residual_stats": {
    "mean": -0.185,
    "std": 3.883,
    "n": 8569
  }
}
```

#### `GET /api/v1/health`
Simple health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-07T15:30:00.123456"
}
```

#### `GET /`
Root endpoint with API information.

## Running the API

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r req.txt
   ```

2. **Run the server:**
   ```bash
   python run_api.py
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build and run:**
   ```bash
   docker-compose up --build
   ```

2. **Or build manually:**
   ```bash
   docker build -t voltcast-api .
   docker run -p 8000:8000 voltcast-api
   ```

## Testing

### Automated Tests
```bash
python test_api.py
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Status
curl http://localhost:8000/api/v1/status

# Prediction
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

## Configuration

### Environment Variables
- `GOLDEN_TOL_ABS`: Verification tolerance (default: 0.5)
- `TF_CPP_MIN_LOG_LEVEL`: TensorFlow log level (default: 2)

### Startup Validation
The API performs these checks on startup:
1. Load manifest.json
2. Validate all artifact paths exist
3. Load all models and scalers
4. Initialize predictor
5. Print model information

If any step fails, the API won't start.

## Feature Engineering

The API reconstructs 59 engineered features:

### Temporal Features (8)
- `hour_cos/sin`: Cyclical hour encoding
- `dow_cos/sin`: Day of week encoding  
- `doy_cos/sin`: Day of year encoding
- `month_cos/sin`: Month encoding

### Weather Features (5)
- `temperature`: Input temperature
- `solar_generation`: Input solar generation
- `humidity`: Input or default (50%)
- `cloud_cover`: Input or default (50%)
- `heat_index`: Calculated heat index

### Derived Features (2)
- `temp_solar_interaction`: Temperature × Solar
- `temp_humidity_interaction`: Temperature × Humidity

### Lag Features (18)
- Demand lags: 1, 2, 3, 6, 12, 24, 48, 72, 168 hours
- Temperature lags: 1, 2, 3, 6, 12, 24, 48, 72, 168 hours

### Rolling Statistics (16)
- Windows: 6, 12, 24, 168 hours
- Stats: mean, std, q25, q75

### Other Features (10)
- Differences: 1h, 24h, 2nd order
- FFT components: 1, 2, 3 (168h period)
- Flags: weekend, holiday
- Holiday distances: days since/to

**Note:** Current implementation uses placeholders for lag/rolling features. Production deployment would need historical data pipeline.

## Model Pipeline

### 1. Feature Building
```python
features = feature_builder.build_from_raw(
    timestamp=datetime,
    temperature=float,
    solar_generation=float,
    humidity=float,
    cloud_cover=float
)
```

### 2. Vector Construction
```python
# XGBoost vector (unscaled)
xgb_vector = feature_builder.build_vector(features)

# Transformer sequence (scaled)
transformer_seq = feature_builder.build_sequence(features, seq_len=168)
```

### 3. Predictions
```python
# Baseline prediction
baseline = xgb_model.predict(xgb_vector)

# Residual correction
residuals = transformer_model.predict(transformer_seq)

# Hybrid result
hybrid = baseline + residuals[0]
```

### 4. Confidence Intervals
```python
# 95% confidence interval
margin = 1.96 * residual_std  # ±7.61 MW
ci_lower = max(0, hybrid - margin)
ci_upper = hybrid + margin
```

## Performance

### Typical Response Times
- Single prediction: ~50-100ms
- Horizon prediction (24h): ~100-200ms
- Status endpoint: ~5-10ms
- Health check: ~1-2ms

### Resource Usage
- Memory: ~2-3 GB (models loaded)
- CPU: Low (inference only)
- Disk: ~500 MB (artifacts)

## Troubleshooting

### Common Issues

**1. TensorFlow DLL Errors**
- Ensure compatible TensorFlow version
- Use Docker for consistent environment

**2. Model Loading Failures**
- Check artifact paths in manifest.json
- Verify file permissions
- Check disk space

**3. Prediction Errors**
- Validate input ranges
- Check feature engineering logic
- Monitor for NaN/inf values

**4. Performance Issues**
- Monitor memory usage
- Consider model quantization
- Add request caching

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python run_api.py
```

### Verification
```bash
# Run verification against golden samples
python scripts/verify_run.py
```
