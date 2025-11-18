# Hybrid Predictor Guide

## Overview

The Hybrid Predictor implements the **LightGBM + Transformer Residual** model architecture from the notebook. It provides two types of predictions:

1. **24-Hour Day-Ahead Predictions**: Hourly load forecasts for the next 24 hours
2. **7-Day Daily Mean Predictions**: Daily average load forecasts for the next 7 days

## Model Architecture

```
Input Features (17 features from CSV)
         ↓
    LightGBM Model
         ↓
   Baseline Prediction
         +
   Transformer Model (on historical residuals)
         ↓
   Residual Correction
         =
   Final Hybrid Prediction
```

### Key Components

1. **LightGBM Baseline** (`lgbm_model.txt`)
   - Trained on 17 engineered features
   - Provides base load prediction
   - Features: temporal (dow, hour, month), weather (temperature, humidity, wind, solar, precipitation), lags (1h, 24h, 168h), rolling means (24h, 168h)

2. **Transformer Residual Model** (`transformer_residual.pt`)
   - PyTorch Transformer with 168-hour sequence length
   - Predicts residual corrections
   - Architecture: 64 d_model, 4 heads, 2 layers
   - Input: Last 168 hours of scaled residuals

3. **Residual Scaler** (`residual_scaler.pkl`)
   - StandardScaler for residual normalization
   - Mean: 9.11, Std: 89.52

## Expected Performance

Based on notebook validation on 2024 test set:

| Metric | LightGBM Baseline | Hybrid Model | Improvement |
|--------|------------------|--------------|-------------|
| MAPE   | 1.9627%          | 1.7938%      | -8.6%       |
| RMSE   | 153.82 MW        | 143.81 MW    | -6.5%       |

## Usage

### 1. Initialize Predictor

```python
from api.services.model_loader import ModelLoader
from api.services.hybrid_predictor import HybridPredictor

# Load models
model_loader = ModelLoader()
model_loader.load_all()

# Initialize predictor
predictor = HybridPredictor(model_loader, use_db=False)
```

### 2. 24-Hour Day-Ahead Prediction

```python
result = predictor.predict_24h_from_csv(
    csv_path='scripts/master_db.csv',
    start_timestamp='2024-01-01 23:00:00',
    return_metrics=True
)

# Access results
print(f"Predictions: {result['predictions']}")  # 24 hourly values
print(f"Actuals: {result['actuals']}")          # 24 actual values
print(f"MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
print(f"MAE: {result['metrics']['hybrid']['mae']:.2f} MW")
```

**Output Structure:**
```python
{
    'start_timestamp': '2024-01-01 23:00:00',
    'timestamps': ['2024-01-01T23:00:00', ...],  # 24 timestamps
    'predictions': [2952.21, 3178.69, ...],      # 24 hybrid predictions
    'baselines': [2954.45, 3180.12, ...],        # 24 LGBM baselines
    'residuals': [-2.24, -1.43, ...],            # 24 residual corrections
    'actuals': [3683.54, 3491.73, ...],          # 24 actual values
    'metrics': {
        'hybrid': {
            'mae': 146.14,
            'mape': 3.9887,
            'rmse': 211.61
        },
        'lgbm_baseline': {
            'mae': 148.62,
            'mape': 4.0564,
            'rmse': 216.66
        }
    }
}
```

### 3. 7-Day Daily Mean Prediction

```python
result = predictor.predict_7day_daily_means_from_csv(
    csv_path='scripts/master_db.csv',
    start_timestamp='2024-01-01 23:00:00',
    return_metrics=True
)

# Access results
print(f"Daily Means: {result['daily_mean_predictions']}")  # 7 daily values
print(f"MAPE: {result['metrics']['hybrid']['mape']:.4f}%")
```

**Output Structure:**
```python
{
    'start_timestamp': '2024-01-01 23:00:00',
    'daily_dates': ['2024-01-01', '2024-01-02', ...],  # 7 dates
    'daily_mean_predictions': [3750.87, 3536.02, ...], # 7 daily means
    'daily_mean_baselines': [3753.12, 3538.45, ...],   # 7 baseline means
    'daily_mean_actuals': [3810.03, 3556.63, ...],     # 7 actual means
    'hourly_predictions': [...],                        # 168 hourly values
    'hourly_actuals': [...],                            # 168 actual values
    'metrics': {
        'hybrid': {
            'mae': 40.16,
            'mape': 1.0948,
            'rmse': 44.34
        },
        'lgbm_baseline': {
            'mae': 43.58,
            'mape': 1.1893,
            'rmse': 47.59
        }
    }
}
```

## Data Requirements

### CSV Format

The CSV must contain these 20 columns (matching notebook training data):

```
timestamp, load, temperature_2m, relativehumidity_2m, apparent_temperature,
shortwave_radiation, precipitation, wind_speed_10m, is_holiday, is_weekend,
month, hour_of_week, heat_index, lag_1, lag_24, lag_168, roll24, roll168,
dow, hour
```

### Feature Descriptions

| Feature | Description | Unit |
|---------|-------------|------|
| timestamp | Datetime | YYYY-MM-DD HH:MM:SS |
| load | Actual load (target) | MW |
| temperature_2m | Temperature at 2m | °C |
| relativehumidity_2m | Relative humidity | % |
| apparent_temperature | Feels-like temperature | °C |
| shortwave_radiation | Solar radiation | W/m² |
| precipitation | Precipitation | mm |
| wind_speed_10m | Wind speed at 10m | m/s |
| is_holiday | Holiday flag | 0/1 |
| is_weekend | Weekend flag | 0/1 |
| month | Month of year | 1-12 |
| hour_of_week | Hour of week | 0-167 |
| heat_index | Heat index | °C |
| lag_1 | Load 1 hour ago | MW |
| lag_24 | Load 24 hours ago | MW |
| lag_168 | Load 168 hours ago | MW |
| roll24 | 24-hour rolling mean | MW |
| roll168 | 168-hour rolling mean | MW |
| dow | Day of week | 0-6 |
| hour | Hour of day | 0-23 |

### Historical Data Requirements

- **Minimum**: 168 hours (7 days) of history before prediction start
- **Recommended**: Full training history for best accuracy

## Testing

Run the validation script:

```bash
python scripts/test_hybrid_predictions.py
```

This will:
1. Test 24-hour prediction on 2024 data
2. Evaluate full 2024 test set (30 days)
3. Test 7-day daily mean predictions
4. Test on 2025 data (if available)

## Datasets

### master_db.csv
- **Period**: 2021-01-08 to 2024-12-31
- **Rows**: 34,896 hours
- **Use**: Training and 2024 validation

### 2025_master_db.csv
- **Period**: 2025-01-01 onwards
- **Use**: Future predictions and validation

## Implementation Details

### Prediction Process

1. **Load historical data** from CSV
2. **Compute historical residuals**:
   - Get last 168 hours before prediction start
   - Build feature vectors for each hour
   - Get LGBM predictions
   - Compute residuals = actual - predicted
   - Scale residuals using StandardScaler

3. **For each prediction hour**:
   - Build feature vector from CSV row
   - Get LGBM baseline prediction
   - Use last 168 scaled residuals as Transformer input
   - Get Transformer residual prediction
   - Unscale residual
   - Hybrid = baseline + residual
   - Update residual sequence for next hour

4. **Compute metrics** (if actuals available):
   - MAE: Mean Absolute Error
   - MAPE: Mean Absolute Percentage Error
   - RMSE: Root Mean Squared Error

### Key Differences from Notebook

The implementation matches the notebook exactly:
- Same 17 features in same order
- Same LightGBM model (loaded from .txt)
- Same Transformer architecture (64/4/2/128)
- Same residual scaling approach
- Same 168-hour sequence length

## Troubleshooting

### Error: "Insufficient history"
- Ensure CSV has at least 168 hours before prediction start
- Check timestamp format matches CSV

### Error: "Timestamp not found"
- Verify timestamp exists in CSV
- Check timestamp format: 'YYYY-MM-DD HH:MM:SS'

### Poor accuracy
- Verify CSV has all 20 required columns
- Check feature values are reasonable
- Ensure historical data quality

### Model loading errors
- Verify artifacts exist:
  - `artifacts/lgbm_model.txt`
  - `artifacts/transformer_residual.pt`
  - `artifacts/residual_scaler.pkl`
  - `artifacts/feature_order.json`

## API Integration

To integrate with existing API:

```python
# In api/routes/predictions.py
from api.services.hybrid_predictor import HybridPredictor

@router.post("/predict/24h")
async def predict_24h(request: PredictionRequest):
    predictor = HybridPredictor(model_loader, use_db=False)
    result = predictor.predict_24h_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp=request.timestamp,
        return_metrics=False
    )
    return result

@router.post("/predict/weekly")
async def predict_weekly(request: PredictionRequest):
    predictor = HybridPredictor(model_loader, use_db=False)
    result = predictor.predict_7day_daily_means_from_csv(
        csv_path='scripts/master_db.csv',
        start_timestamp=request.timestamp,
        return_metrics=False
    )
    return result
```

## Performance Notes

- **24-hour prediction**: ~1-2 seconds
- **7-day prediction**: ~5-10 seconds
- Memory usage: ~500MB (models loaded)
- GPU not required (CPU inference is fast)

## Future Enhancements

1. **Database Integration**: Load data from PostgreSQL instead of CSV
2. **Real-time Weather**: Fetch weather forecasts from API
3. **Confidence Intervals**: Add uncertainty quantification
4. **Batch Predictions**: Optimize for multiple predictions
5. **Model Retraining**: Automated retraining pipeline
