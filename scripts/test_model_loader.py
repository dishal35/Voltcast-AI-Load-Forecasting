"""
Test ModelLoader validation including DB check.
"""

import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.model_loader import ModelLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test model loader."""
    logger.info("Testing ModelLoader...")
    logger.info("=" * 60)
    
    try:
        # Initialize loader
        loader = ModelLoader()
        
        # Validate artifacts
        logger.info("\n1. Artifact Validation:")
        artifacts = loader.validate_artifacts()
        for name, exists in artifacts.items():
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {name}: {exists}")
        
        if not all(artifacts.values()):
            logger.error("\n✗ Some artifacts missing!")
            sys.exit(1)
        
        # Validate database
        logger.info("\n2. Database Validation:")
        db_status = loader.validate_database()
        logger.info(f"  Available: {db_status.get('available')}")
        if db_status.get('available'):
            logger.info(f"  Row count: {db_status.get('row_count'):,}")
            logger.info(f"  Latest timestamp: {db_status.get('latest_timestamp')}")
            logger.info(f"  Sufficient for sequences: {db_status.get('sufficient_for_sequence')}")
        else:
            logger.warning(f"  Error: {db_status.get('error')}")
        
        # Load all models
        logger.info("\n3. Loading Models:")
        loader.load_all()
        
        # Check loaded models
        logger.info("\n4. Loaded Models:")
        logger.info(f"  XGBoost: {loader.xgb_model is not None}")
        logger.info(f"  Transformer: {loader.transformer_model is not None}")
        logger.info(f"  SARIMAX: {loader.sarimax_model is not None}")
        logger.info(f"  Feature order: {len(loader.feature_order)} features")
        
        # Get manifest info
        manifest = loader.get_manifest()
        hourly = manifest.get("models", {}).get("hourly", {})
        metrics = hourly.get("performance_metrics", {}).get("hybrid", {})
        
        logger.info("\n5. Model Metrics:")
        logger.info(f"  MAE: {metrics.get('mae', 0):.4f} MW")
        logger.info(f"  RMSE: {metrics.get('rmse', 0):.4f} MW")
        logger.info(f"  MAPE: {metrics.get('mape', 0):.4f}%")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL CHECKS PASSED")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n✗ VALIDATION FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
