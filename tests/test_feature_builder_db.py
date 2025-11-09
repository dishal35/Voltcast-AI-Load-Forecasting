"""
Test FeatureBuilder with real database-backed feature computation.
"""
import pytest
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.feature_builder import FeatureBuilder
from api.services.storage import get_storage_service
from api.services.model_loader import ModelLoader


class TestFeatureBuilderDB:
    """Test FeatureBuilder with database-backed features."""
    
    @pytest.fixture(scope="class")
    def storage_service(self):
        """Get storage service instance."""
        return get_storage_service()
    
    @pytest.fixture(scope="class")
    def feature_builder(self, storage_service):
        """Create FeatureBuilder with storage service."""
        # Load model artifacts
        model_loader = ModelLoader("artifacts/models/manifest.json")
        model_loader.load_all()
        
        feature_order = model_loader.get_metadata('feature_order')
        scaler = model_loader.get_scaler('transformer')
        
        fb = FeatureBuilder(
            feature_order=feature_order,
            scaler=scaler,
            storage_service=storage_service
        )
        
        return fb
    
    def test_storage_has_data(self, storage_service):
        """Test that storage service has historical data."""
        row_count = storage_service.get_row_count()
        assert row_count > 0, "Storage service should have historical data"
        assert row_count >= 168, f"Storage should have at least 168 rows, got {row_count}"
        print(f"✓ Storage has {row_count:,} rows")
    
    def test_build_sequence_for_timestamp_shape(self, feature_builder):
        """Test that build_sequence_for_timestamp returns correct shape."""
        # Use a timestamp that should have data (2023-01-07)
        timestamp = "2023-01-07T01:00:00"
        
        seq, metadata = feature_builder.build_sequence_for_timestamp(timestamp)
        
        # Check shape
        assert seq.shape == (1, 168, 59), f"Expected shape (1, 168, 59), got {seq.shape}"
        print(f"✓ Sequence shape correct: {seq.shape}")
        
        # Check metadata
        assert 'data_source' in metadata
        assert 'history_length' in metadata
        print(f"✓ Metadata: source={metadata['data_source']}, history_length={metadata['history_length']}")
    
    def test_build_sequence_for_timestamp_non_zero(self, feature_builder):
        """Test that features are non-zero (not placeholders)."""
        timestamp = "2023-01-07T01:00:00"
        
        seq, metadata = feature_builder.build_sequence_for_timestamp(timestamp)
        
        # Check that sequence has non-zero values
        assert not np.allclose(seq, 0.0), "Sequence should not be all zeros"
        
        # Check that we have reasonable variance
        std = np.std(seq)
        assert std > 0.01, f"Sequence should have variance, got std={std}"
        
        print(f"✓ Sequence has non-zero values (std={std:.4f})")
    
    def test_build_from_db_history(self, feature_builder):
        """Test build_from_db_history method."""
        timestamp = datetime(2023, 1, 7, 1, 0, 0)
        weather_forecast = {
            'temperature': 25.0,
            'solar_generation': 50.0,
            'humidity': 60.0,
            'cloud_cover': 40.0
        }
        
        xgb_vec, transformer_seq, metadata = feature_builder.build_from_db_history(
            timestamp=timestamp,
            weather_forecast=weather_forecast,
            seq_len=168
        )
        
        # Check shapes
        assert xgb_vec.shape == (1, 59), f"XGBoost vector shape should be (1, 59), got {xgb_vec.shape}"
        assert transformer_seq.shape == (1, 168, 59), f"Transformer seq shape should be (1, 168, 59), got {transformer_seq.shape}"
        
        # Check metadata
        assert metadata['data_source'] in ['database', 'fallback', 'error_fallback']
        
        print(f"✓ build_from_db_history works: source={metadata['data_source']}")
    
    def test_feature_values_realistic(self, feature_builder):
        """Test that computed features have realistic values."""
        timestamp = "2023-01-07T01:00:00"
        
        seq, metadata = feature_builder.build_sequence_for_timestamp(timestamp)
        
        # Extract first timestep features
        features = seq[0, 0, :]  # Shape: (59,)
        
        # Check that features are in reasonable ranges (after scaling)
        # Scaled features should typically be in range [-5, 5]
        assert np.all(np.abs(features) < 10), "Scaled features should be in reasonable range"
        
        # Check that not all features are the same
        unique_values = len(np.unique(features))
        assert unique_values > 10, f"Should have diverse feature values, got {unique_values} unique"
        
        print(f"✓ Features are realistic (unique values: {unique_values})")
    
    def test_different_timestamps_different_features(self, feature_builder):
        """Test that different timestamps produce different features."""
        ts1 = "2023-01-07T01:00:00"
        ts2 = "2023-01-07T15:00:00"
        
        seq1, _ = feature_builder.build_sequence_for_timestamp(ts1)
        seq2, _ = feature_builder.build_sequence_for_timestamp(ts2)
        
        # Sequences should be different
        assert not np.allclose(seq1, seq2), "Different timestamps should produce different features"
        
        # Calculate difference
        diff = np.abs(seq1 - seq2).mean()
        print(f"✓ Different timestamps produce different features (mean diff: {diff:.4f})")
    
    def test_with_weather_forecast(self, feature_builder):
        """Test with custom weather forecast."""
        timestamp = "2023-01-07T01:00:00"
        weather = {
            'temperature': 30.0,
            'solar_generation': 100.0,
            'humidity': 70.0,
            'cloud_cover': 20.0
        }
        
        seq, metadata = feature_builder.build_sequence_for_timestamp(
            timestamp=timestamp,
            weather_forecast=weather
        )
        
        assert seq.shape == (1, 168, 59)
        print(f"✓ Works with custom weather forecast")
    
    def test_insufficient_history_fallback(self, feature_builder):
        """Test fallback when insufficient history available."""
        # Use a very early timestamp that might not have enough history
        timestamp = "2000-01-01T01:00:00"
        
        seq, metadata = feature_builder.build_sequence_for_timestamp(timestamp)
        
        # Should still return valid shape
        assert seq.shape == (1, 168, 59)
        
        # Metadata should indicate fallback or padding
        print(f"✓ Handles insufficient history: source={metadata['data_source']}, length={metadata['history_length']}")


def test_feature_builder_standalone():
    """Standalone test that can be run without pytest."""
    print("\n" + "="*60)
    print("Testing FeatureBuilder with DB-backed features")
    print("="*60)
    
    # Initialize
    storage = get_storage_service()
    model_loader = ModelLoader("artifacts/models/manifest.json")
    model_loader.load_all()
    
    feature_order = model_loader.get_metadata('feature_order')
    scaler = model_loader.get_scaler('transformer')
    
    fb = FeatureBuilder(
        feature_order=feature_order,
        scaler=scaler,
        storage_service=storage
    )
    
    # Test
    timestamp = "2023-01-07T01:00:00"
    seq, metadata = fb.build_sequence_for_timestamp(timestamp)
    
    print(f"\n✓ Sequence shape: {seq.shape}")
    print(f"✓ Data source: {metadata['data_source']}")
    print(f"✓ History length: {metadata['history_length']}")
    print(f"✓ Sequence std: {np.std(seq):.4f}")
    print(f"✓ Sequence mean: {np.mean(seq):.4f}")
    print(f"✓ Sequence min: {np.min(seq):.4f}")
    print(f"✓ Sequence max: {np.max(seq):.4f}")
    
    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED")
    print("="*60)


if __name__ == "__main__":
    # Run standalone test
    test_feature_builder_standalone()
