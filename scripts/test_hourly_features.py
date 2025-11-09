"""
Test script to verify hourly features are varying correctly.
"""
from datetime import datetime, timedelta
from api.services.feature_builder import FeatureBuilder
from api.services.model_loader import ModelLoader
from api.services.storage import get_storage_service
import numpy as np

# Load model artifacts
model_loader = ModelLoader('artifacts/models/manifest.json')
model_loader.load_all()

# Create feature builder
storage = get_storage_service()
feature_builder = FeatureBuilder(
    feature_order=model_loader.get_metadata('feature_order'),
    scaler=model_loader.get_scaler('transformer'),
    storage_service=storage
)

# Test date
test_date = datetime(2023, 1, 7, 0, 0, 0)

# Get historical data once
history_df = storage.get_last_n_hours(168, until_ts=test_date)
print(f"History length: {len(history_df)}")

# Weather forecast (constant for testing)
weather = {
    'temperature': 25.0,
    'humidity': 60.0,
    'wind_speed': 3.5,
    'cloud_cover': 40.0,
    'solar_generation': 50.0,
}

print("\nTesting features for different hours:")
print("=" * 80)

for hour in [0, 6, 12, 18, 23]:
    hour_timestamp = test_date + timedelta(hours=hour)
    
    # Compute features
    features = feature_builder._compute_features_from_history(
        timestamp=hour_timestamp,
        history_df=history_df,
        weather_forecast=weather
    )
    
    # Build vector
    vector = feature_builder.build_vector(features)
    
    # Get XGBoost model
    xgb_model = model_loader.get_model('xgboost')
    prediction = xgb_model.predict(vector.reshape(1, -1))[0]
    
    print(f"\nHour {hour:02d}:00")
    print(f"  hour_cos: {features['hour_cos']:.4f}")
    print(f"  hour_sin: {features['hour_sin']:.4f}")
    print(f"  demand_lag_1: {features.get('demand_lag_1', 0):.2f}")
    print(f"  demand_lag_24: {features.get('demand_lag_24', 0):.2f}")
    print(f"  XGBoost prediction: {prediction:.2f} MW")

print("\n" + "=" * 80)
print("✓ Feature test complete")
