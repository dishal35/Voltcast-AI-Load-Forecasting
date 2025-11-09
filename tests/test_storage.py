"""
Unit tests for storage service.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from api.services.storage import StorageService


@pytest.fixture
def storage():
    """Create a test storage service with SQLite."""
    service = StorageService('sqlite:///:memory:')
    service.initialize_schema()
    return service


@pytest.fixture
def sample_data():
    """Create sample hourly data."""
    base_time = datetime(2023, 1, 1, 0, 0)
    data = []
    
    for i in range(200):  # 200 hours of data
        data.append({
            'ts': base_time + timedelta(hours=i),
            'demand': 1000 + i * 10,
            'temperature': 20 + (i % 24),
            'humidity': 50 + (i % 30),
            'wind_speed': 5 + (i % 10),
            'solar_generation': 100 if 6 <= (i % 24) <= 18 else 0,
            'cloud_cover': 30 + (i % 40),
            'is_holiday': i % 168 == 0  # Weekly holiday
        })
    
    return pd.DataFrame(data)


def test_initialize_schema(storage):
    """Test schema initialization."""
    # Should not raise any errors
    storage.initialize_schema()
    
    # Check row count is 0
    assert storage.get_row_count() == 0


def test_append_actuals(storage, sample_data):
    """Test inserting data."""
    rows = storage.append_actuals(sample_data)
    
    assert rows == len(sample_data)
    assert storage.get_row_count() == len(sample_data)


def test_get_last_n_hours(storage, sample_data):
    """Test retrieving last N hours."""
    storage.append_actuals(sample_data)
    
    # Get last 168 hours
    result = storage.get_last_n_hours(168)
    
    assert len(result) == 168
    assert list(result.columns) == [
        'ts', 'demand', 'temperature', 'humidity', 'wind_speed',
        'solar_generation', 'cloud_cover', 'is_holiday'
    ]
    
    # Check ordering (oldest first)
    assert result['ts'].is_monotonic_increasing
    
    # Check values match
    expected_start = sample_data.iloc[-168]['ts']
    assert result.iloc[0]['ts'] == expected_start


def test_get_last_n_hours_with_until_ts(storage, sample_data):
    """Test retrieving data until specific timestamp."""
    storage.append_actuals(sample_data)
    
    # Get 24 hours before the 100th hour
    until_ts = sample_data.iloc[100]['ts']
    result = storage.get_last_n_hours(24, until_ts=until_ts)
    
    assert len(result) == 24
    assert result.iloc[-1]['ts'] < until_ts
    
    # Should be hours 76-99
    expected_start = sample_data.iloc[76]['ts']
    assert result.iloc[0]['ts'] == expected_start


def test_get_last_n_hours_insufficient_data(storage, sample_data):
    """Test behavior when insufficient data available."""
    # Insert only 50 hours
    storage.append_actuals(sample_data.iloc[:50])
    
    # Request 168 hours - should return 50 with warning
    result = storage.get_last_n_hours(168)
    
    assert len(result) == 50


def test_get_last_n_hours_no_data(storage):
    """Test error when no data available."""
    with pytest.raises(ValueError, match="No historical data found"):
        storage.get_last_n_hours(24)


def test_get_range(storage, sample_data):
    """Test retrieving data for specific range."""
    storage.append_actuals(sample_data)
    
    start_ts = sample_data.iloc[50]['ts']
    end_ts = sample_data.iloc[100]['ts']
    
    result = storage.get_range(start_ts, end_ts)
    
    assert len(result) == 50
    assert result.iloc[0]['ts'] == start_ts
    assert result.iloc[-1]['ts'] < end_ts


def test_get_latest_timestamp(storage, sample_data):
    """Test getting latest timestamp."""
    assert storage.get_latest_timestamp() is None
    
    storage.append_actuals(sample_data)
    
    latest = storage.get_latest_timestamp()
    assert latest == sample_data['ts'].max()


def test_upsert_behavior(storage, sample_data):
    """Test that duplicate timestamps are updated, not duplicated."""
    # Insert first 100 rows
    storage.append_actuals(sample_data.iloc[:100])
    assert storage.get_row_count() == 100
    
    # Modify and re-insert overlapping data (rows 50-150)
    modified_data = sample_data.iloc[50:150].copy()
    modified_data['demand'] = modified_data['demand'] * 2
    
    storage.append_actuals(modified_data)
    
    # Should still have 150 unique rows (not 200)
    assert storage.get_row_count() == 150
    
    # Check that row 75 has updated demand value
    result = storage.get_range(
        sample_data.iloc[75]['ts'],
        sample_data.iloc[76]['ts']
    )
    assert result.iloc[0]['demand'] == sample_data.iloc[75]['demand'] * 2


def test_missing_optional_columns(storage):
    """Test inserting data with only required columns."""
    df = pd.DataFrame({
        'ts': [datetime(2023, 1, 1, i) for i in range(10)],
        'demand': [1000 + i * 10 for i in range(10)]
    })
    
    rows = storage.append_actuals(df)
    assert rows == 10
    
    result = storage.get_last_n_hours(10)
    assert len(result) == 10
    assert result['temperature'].isna().all()


def test_deterministic_ordering(storage, sample_data):
    """Test that get_last_n_hours returns consistent ordering."""
    storage.append_actuals(sample_data)
    
    # Call multiple times
    result1 = storage.get_last_n_hours(168)
    result2 = storage.get_last_n_hours(168)
    
    pd.testing.assert_frame_equal(result1, result2)
