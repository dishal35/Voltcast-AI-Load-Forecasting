"""
Test script for LightGBM + PyTorch Transformer migration.
Verifies that the new model loads and makes predictions correctly.
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

from api.services.model_loader import ModelLoader
from api.services.predictor import HybridPredictor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_model_loading():
    """Test that models load correctly."""
    print("\n" + "="*60)
    print("TEST 1: Model Loading")
    print("="*60)
    
    try:
        loader = ModelLoader()
        loader.load_all()
        
        # Check artifacts
        checks = loader.validate_artifacts()
        print("\nArtifact Validation:")
        for name, exists in checks.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {name}: {exists}")
        
        # Check models
        print("\nLoaded Models:")
        print(f"  LightGBM: {loader.lgbm_model is not None}")
        print(f"  Transformer: {loader.transformer_model is not None}")
        print(f"  Residual Scaler: {loader.get_scaler('residual') is not None}")
        
        # Check feature order
        feature_order = loader.feature_order
        print(f"\nFeature Count: {len(feature_order)}")
        print(f"Features: {feature_order}")
        
        return loader
        
    except Exception as e:
        print(f"\n[FAILED] Model loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_single_prediction(loader):
    """Test single hour prediction."""
    print("\n" + "="*60)
    print("TEST 2: Single Hour Prediction")
    print("="*60)
    
    try:
        predictor = HybridPredictor(loader, use_db=True)
        
        # Test prediction
        timestamp = datetime(2024, 7, 15, 10, 0, 0)
        result = predictor.predict(
            timestamp=timestamp,
            temperature=30.0,
            solar_generation=80.0,
            humidity=65.0,
            return_components=True
        )
        
        print(f"\nPrediction for {timestamp}:")
        print(f"  Hybrid: {result['prediction']:.2f}")
        print(f"  Baseline: {result['components']['baseline']:.2f}")
        print(f"  Residual: {result['components']['residual']:.2f}")
        print(f"  Confidence: {result['confidence_score']:.1f}%")
        print(f"  Data Source: {result['metadata']['data_source']}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Single prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_horizon_prediction(loader):
    """Test 24-hour horizon prediction."""
    print("\n" + "="*60)
    print("TEST 3: 24-Hour Horizon Prediction")
    print("="*60)
    
    try:
        predictor = HybridPredictor(loader, use_db=True)
        
        # Test horizon prediction
        timestamp = datetime(2024, 7, 15, 0, 0, 0)
        result = predictor.predict_horizon(
            timestamp=timestamp,
            temperature=28.0,
            solar_generation=70.0,
            horizon=24
        )
        
        print(f"\n24-Hour Forecast starting {timestamp}:")
        print(f"  Predictions: {len(result['predictions'])} hours")
        print(f"  First 5 hours: {result['predictions'][:5]}")
        print(f"  Data Source: {result['metadata']['data_source']}")
        print(f"  History Length: {result['metadata']['history_length']}")
        
        return True
        
    except Exception as e:
        print(f"\n[FAILED] Horizon prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("LGBM + PyTorch Transformer Migration Test")
    print("="*60)
    
    # Test 1: Model Loading
    loader = test_model_loading()
    if loader is None:
        print("\n[FAILED] Could not load models")
        return False
    
    # Test 2: Single Prediction
    if not test_single_prediction(loader):
        print("\n[FAILED] Single prediction test")
        return False
    
    # Test 3: Horizon Prediction
    if not test_horizon_prediction(loader):
        print("\n[FAILED] Horizon prediction test")
        return False
    
    print("\n" + "="*60)
    print("[SUCCESS] ALL TESTS PASSED")
    print("="*60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
