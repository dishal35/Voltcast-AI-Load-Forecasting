"""
Test FeatureBuilder with real database-backed feature computation.
Simple test script without pytest dependency.
"""
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.feature_builder import FeatureBuilder
from api.services.storage import get_storage_service
from api.services.model_loader import ModelLoader


def test_feature_builder_db():
    """Test FeatureBuilder with DB-backed features."""
    print("\n" + "="*70)
    print("Testing FeatureBuilder with DB-backed Feature Computation")
    print("="*70)
    
    try:
        # Initialize storage
        print("\n1. Initializing storage service...")
        storage = get_storage_service()
        row_count = storage.get_row_count()
        print(f"   ✓ Storage has {row_count:,} rows")
        
        if row_count < 168:
            print(f"   ✗ ERROR: Need at least 168 rows, got {row_count}")
            return False
        
        # Initialize model loader
        print("\n2. Loading model artifacts...")
        model_loader = ModelLoader("artifacts/models/manifest.json")
        model_loader.load_all()
        print("   ✓ Models loaded")
        
        # Get feature order and scaler
        feature_order = model_loader.get_metadata('feature_order')
        scaler = model_loader.get_scaler('transformer')
        print(f"   ✓ Feature order: {len(feature_order)} features")
        
        # Create FeatureBuilder
        print("\n3. Creating FeatureBuilder with storage...")
        fb = FeatureBuilder(
            feature_order=feature_order,
            scaler=scaler,
            storage_service=storage
        )
        print("   ✓ FeatureBuilder initialized")
        
        # Test 1: build_sequence_for_timestamp
        print("\n4. Testing build_sequence_for_timestamp()...")
        timestamp = "2023-01-07T01:00:00"
        seq, metadata = fb.build_sequence_for_timestamp(timestamp)
        
        print(f"   ✓ Sequence shape: {seq.shape}")
        assert seq.shape == (1, 168, 59), f"Expected (1, 168, 59), got {seq.shape}"
        
        print(f"   ✓ Data source: {metadata['data_source']}")
        print(f"   ✓ History length: {metadata['history_length']}")
        
        # Test 2: Check non-zero values
        print("\n5. Checking feature values...")
        std = np.std(seq)
        mean = np.mean(seq)
        min_val = np.min(seq)
        max_val = np.max(seq)
        
        print(f"   ✓ Std: {std:.4f}")
        print(f"   ✓ Mean: {mean:.4f}")
        print(f"   ✓ Min: {min_val:.4f}")
        print(f"   ✓ Max: {max_val:.4f}")
        
        assert std > 0.01, f"Sequence should have variance, got std={std}"
        assert not np.allclose(seq, 0.0), "Sequence should not be all zeros"
        
        # Test 3: Different timestamps produce different features
        print("\n6. Testing different timestamps...")
        ts1 = "2023-01-07T01:00:00"
        ts2 = "2023-01-07T15:00:00"
        
        seq1, _ = fb.build_sequence_for_timestamp(ts1)
        seq2, _ = fb.build_sequence_for_timestamp(ts2)
        
        diff = np.abs(seq1 - seq2).mean()
        print(f"   ✓ Mean difference: {diff:.4f}")
        assert not np.allclose(seq1, seq2), "Different timestamps should produce different features"
        
        # Test 4: With custom weather forecast
        print("\n7. Testing with custom weather forecast...")
        weather = {
            'temperature': 30.0,
            'solar_generation': 100.0,
            'humidity': 70.0,
            'cloud_cover': 20.0
        }
        
        seq_weather, _ = fb.build_sequence_for_timestamp(ts1, weather_forecast=weather)
        assert seq_weather.shape == (1, 168, 59)
        print("   ✓ Works with custom weather forecast")
        
        # Test 5: build_from_db_history
        print("\n8. Testing build_from_db_history()...")
        timestamp_dt = datetime(2023, 1, 7, 1, 0, 0)
        weather_forecast = {
            'temperature': 25.0,
            'solar_generation': 50.0,
            'humidity': 60.0,
            'cloud_cover': 40.0
        }
        
        xgb_vec, transformer_seq, metadata = fb.build_from_db_history(
            timestamp=timestamp_dt,
            weather_forecast=weather_forecast,
            seq_len=168
        )
        
        print(f"   ✓ XGBoost vector shape: {xgb_vec.shape}")
        print(f"   ✓ Transformer seq shape: {transformer_seq.shape}")
        print(f"   ✓ Data source: {metadata['data_source']}")
        
        assert xgb_vec.shape == (1, 59), f"XGBoost vector should be (1, 59), got {xgb_vec.shape}"
        assert transformer_seq.shape == (1, 168, 59), f"Transformer seq should be (1, 168, 59), got {transformer_seq.shape}"
        
        # Test 6: Feature diversity
        print("\n9. Checking feature diversity...")
        features = seq[0, 0, :]  # First timestep
        unique_values = len(np.unique(features))
        print(f"   ✓ Unique feature values: {unique_values}")
        assert unique_values > 10, f"Should have diverse features, got {unique_values}"
        
        # Test 7: Realistic ranges
        print("\n10. Checking feature ranges...")
        # Most features should be in reasonable range (allow some outliers)
        reasonable_count = np.sum(np.abs(features) < 10)
        total_count = len(features)
        pct_reasonable = (reasonable_count / total_count) * 100
        print(f"   ✓ {pct_reasonable:.1f}% of features in range |x| < 10 ({reasonable_count}/{total_count})")
        assert pct_reasonable > 80, f"At least 80% of features should be in reasonable range, got {pct_reasonable:.1f}%"
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        print("\nSummary:")
        print(f"  - Database rows: {row_count:,}")
        print(f"  - Feature count: {len(feature_order)}")
        print(f"  - Sequence shape: (1, 168, 59)")
        print(f"  - Data source: {metadata['data_source']}")
        print(f"  - Feature std: {std:.4f}")
        print(f"  - Unique values: {unique_values}")
        print("\n✓ FeatureBuilder is working with real DB-backed features!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_feature_builder_db()
    sys.exit(0 if success else 1)
