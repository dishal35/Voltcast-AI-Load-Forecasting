"""
Unit tests for feature builder with DB integration.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from api.services.feature_builder import FeatureBuilder
from api.services.storage import StorageService


@pytest.fixture
def feature_order():
    """Sample feature order (subset for testing)."""
    return [
        'hour_cos', 'hour_sin', 'dow_cos', 'dow_sin',
        'temperature', 'solar_generation', 'humidity', 'cloud_cover',
        'demand_lag_1', 'demand_lag_24', 'demand_lag_168',
        'demand_roll_mean_24', 'demand_roll_std_24',
        'demand_diff_1h', 'fft_amp_1_168'
    ]


@pytest.fixture
def storage_with_data():
    """Create storage service with sample data."""
    storage = StorageService('sqlite:///:memory:')
    storage.initialize_schema()
    
    # Create 200 hours of sample data
    base_time = datetime(2023, 1, 1, 0, 0)
    data = []
    
    for i in range(200):
        data.append({
            'ts': base_time + timedelta(hours=i),
            'demand': 3000 + 500 * np.sin(2 * np.pi * i / 24) + np.random.randn() * 50,
            'temperature': 25 + 5 * np.sin(2 * np.pi * i / 24),
            'humidity': 60 + 10 * np.sin(2 * np.pi * i / 12),
            'wind_speed': 5 + 2 * np.random.randn(),
            'solar_generation': 100 if 6 <= (i % 24) <= 18 else 0,
            'cloud_cover': 30 + 20 * np.random.randn(),
            'is_holiday': False
        })
    
    df = pd.DataFrame(data)
    storage.append_actuals(df)
    
    return storage


def test_feature_builder_initialization(feature_order):
    """Test basic initialization."""
    builder = FeatureBuilder(feature_order=feature_order)
    
    assert builder.n_features == len(feature_order)
    assert builder.feature_order == feature_order


def test_build_from_raw(feature_order):
    """Test legacy build_from_raw method."""
    builder = FeatureBuilder(feature_order=feature_order)
    
    timestamp = datetime(2023, 6, 15, 14, 0)
    features = builder.build_from_raw(
        timestamp=timestamp,
        temperature=30.0,
        solar_generation=150.0,
        humidity=65.0,
        cloud_cover=20.0
    )
    
    # Check temporal features
    assert 'hour_cos' in features
    assert 'hour_sin' in features
    assert features['temperature'] == 30.0
    assert features['solar_generation'] == 150.0


def test_build_from_db_history(feature_order, storage_with_data):
    """Test building features from database history."""
    builder = FeatureBuilder(
        feature_order=feature_order,
        storage_service=storage_with_data
    )
    
    # Predict for timestamp after available data
    predict_ts = datetime(2023, 1, 9, 12, 0)  # 200+ hours after start
    
    weather_forecast = {
        'temperature': 28.0,
        'humidity': 55.0,
        'wind_speed': 4.0,
        'cloud_cover': 25.0,
        'solar_generation': 120.0
    }
    
    xgb_vec, transformer_seq, metadata = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    # Check shapes
    assert xgb_vec.shape == (1, len(feature_order))
    assert transformer_seq.shape == (1, 168, len(feature_order))
    
    # Check metadata
    assert metadata['data_source'] == 'database'
    assert metadata['history_length'] == 168


def test_build_from_db_insufficient_data(feature_order):
    """Test behavior with insufficient historical data."""
    # Empty storage
    storage = StorageService('sqlite:///:memory:')
    storage.initialize_schema()
    
    builder = FeatureBuilder(
        feature_order=feature_order,
        storage_service=storage
    )
    
    predict_ts = datetime(2023, 1, 1, 12, 0)
    weather_forecast = {'temperature': 25.0, 'solar_generation': 100.0}
    
    xgb_vec, transformer_seq, metadata = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    # Should fallback
    assert metadata['data_source'] in ['fallback', 'error_fallback']
    assert xgb_vec.shape == (1, len(feature_order))


def test_lag_features_computed_correctly(feature_order, storage_with_data):
    """Test that lag features use actual historical values."""
    builder = FeatureBuilder(
        feature_order=feature_order,
        storage_service=storage_with_data
    )
    
    predict_ts = datetime(2023, 1, 9, 0, 0)
    weather_forecast = {'temperature': 25.0, 'solar_generation': 100.0}
    
    # Get history manually
    history = storage_with_data.get_last_n_hours(168, until_ts=predict_ts)
    
    # Build features
    xgb_vec, _, metadata = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    assert metadata['data_source'] == 'database'
    
    # Lag features should not be zero (they were in legacy method)
    # Note: This test assumes demand_lag_1 is in feature_order
    if 'demand_lag_1' in feature_order:
        lag_1_idx = feature_order.index('demand_lag_1')
        lag_1_value = xgb_vec[0, lag_1_idx]
        
        # Should match last demand value from history
        expected_lag_1 = history['demand'].iloc[-1]
        assert abs(lag_1_value - expected_lag_1) < 1.0


def test_rolling_features_computed(feature_order, storage_with_data):
    """Test that rolling statistics are computed from history."""
    builder = FeatureBuilder(
        feature_order=feature_order,
        storage_service=storage_with_data
    )
    
    predict_ts = datetime(2023, 1, 9, 0, 0)
    weather_forecast = {'temperature': 25.0, 'solar_generation': 100.0}
    
    xgb_vec, _, metadata = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    assert metadata['data_source'] == 'database'
    
    # Rolling mean should not be zero
    if 'demand_roll_mean_24' in feature_order:
        roll_mean_idx = feature_order.index('demand_roll_mean_24')
        roll_mean_value = xgb_vec[0, roll_mean_idx]
        
        assert roll_mean_value > 0  # Should have actual value


def test_deterministic_output(feature_order, storage_with_data):
    """Test that same inputs produce same outputs."""
    builder = FeatureBuilder(
        feature_order=feature_order,
        storage_service=storage_with_data
    )
    
    predict_ts = datetime(2023, 1, 9, 0, 0)
    weather_forecast = {'temperature': 25.0, 'solar_generation': 100.0}
    
    # Build twice
    xgb_vec1, seq1, _ = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    xgb_vec2, seq2, _ = builder.build_from_db_history(
        timestamp=predict_ts,
        weather_forecast=weather_forecast,
        seq_len=168
    )
    
    np.testing.assert_array_equal(xgb_vec1, xgb_vec2)
    np.testing.assert_array_equal(seq1, seq2)
