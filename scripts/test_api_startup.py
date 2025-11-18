"""
Quick test to verify API starts correctly
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from api.services.model_loader import ModelLoader
from api.services.predictor import HybridPredictor

print("="*60)
print("Testing API Startup")
print("="*60)

try:
    print("\n1. Loading model artifacts...")
    model_loader = ModelLoader(manifest_path="artifacts/models/manifest.json")
    model_loader.load_all()
    print("   [OK] Models loaded")
    
    print("\n2. Validating artifacts...")
    artifacts = model_loader.validate_artifacts()
    
    required = ['transformer', 'lgbm_baseline', 'residual_scaler', 'feature_order', 'residual_stats']
    missing = [name for name in required if not artifacts.get(name, False)]
    
    if missing:
        print(f"   [FAIL] Missing: {missing}")
        sys.exit(1)
    
    print("   [OK] All required artifacts present")
    
    print("\n3. Initializing predictor...")
    predictor = HybridPredictor(model_loader, use_db=True)
    print("   [OK] Predictor initialized")
    
    print("\n4. Testing single prediction...")
    from datetime import datetime
    result = predictor.predict(
        timestamp=datetime(2025, 1, 8, 10, 0, 0),
        return_components=True
    )
    print(f"   [OK] Prediction: {result['prediction']:.2f} MW")
    
    print("\n" + "="*60)
    print("[SUCCESS] API components working correctly")
    print("="*60)
    print("\nYou can now start the API with: python run_api.py")
    
except Exception as e:
    print(f"\n[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
