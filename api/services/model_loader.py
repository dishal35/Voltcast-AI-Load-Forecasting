"""
Model Loader Service
Loads and manages ML model artifacts.
"""
import json
import joblib
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ModelLoader:
    """Loads and caches model artifacts."""
    
    def __init__(self, manifest_path: str = "artifacts/models/manifest.json"):
        """
        Initialize model loader.
        
        Args:
            manifest_path: Path to manifest.json
        """
        self.base_path = Path(manifest_path).parent.parent.parent
        self.manifest_path = self.base_path / manifest_path
        
        self.manifest = self._load_manifest()
        self.models = {}
        self.scalers = {}
        self.metadata = {}
        
        logger.info(f"ModelLoader initialized with base path: {self.base_path}")
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json"""
        with open(self.manifest_path) as f:
            return json.load(f)
    
    def load_all(self):
        """Load all artifacts specified in manifest."""
        logger.info("Loading all artifacts...")
        
        # Load hourly model artifacts
        hourly = self.manifest.get("models", {}).get("hourly", {})
        
        # Load SARIMAX baseline
        xgb_path = self.base_path / hourly.get("baseline_path", "")
        if xgb_path.exists():
            import xgboost as xgb
            self.models['xgboost'] = xgb.XGBRegressor()
            self.models['xgboost'].load_model(str(xgb_path))
            logger.info(f"✓ Loaded SARIMAX baseline from {xgb_path}")
        
        # Load Transformer
        tf_path = self.base_path / hourly.get("transformer_path", "")
        if tf_path.exists():
            try:
                from tf_keras.models import load_model
                self.models['transformer'] = load_model(str(tf_path))
                logger.info(f"✓ Loaded Transformer from {tf_path}")
            except Exception as e:
                logger.warning(f"Failed to load Transformer: {e}")
        
        # Load scaler
        scaler_path = self.base_path / hourly.get("scaler_path", "")
        if scaler_path.exists():
            self.scalers['transformer'] = joblib.load(str(scaler_path))
            logger.info(f"✓ Loaded scaler from {scaler_path}")
        
        # Load feature order
        feat_path = self.base_path / hourly.get("feature_order_path", "")
        if feat_path.exists():
            with open(feat_path) as f:
                data = json.load(f)
                self.metadata['feature_order'] = data.get("feature_order", data) if isinstance(data, dict) else data
            logger.info(f"✓ Loaded feature order ({len(self.metadata['feature_order'])} features)")
        
        # Load residual stats
        stats_path = self.base_path / hourly.get("residual_stats_path", "")
        if stats_path.exists():
            self.metadata['residual_stats'] = joblib.load(str(stats_path))
            logger.info(f"✓ Loaded residual stats")
        
        # Load SARIMAX weekly model
        weekly = self.manifest.get("models", {}).get("weekly", {})
        sarimax_path = self.base_path / weekly.get("path", "")
        if sarimax_path.exists():
            self.models['sarimax'] = joblib.load(str(sarimax_path))
            logger.info(f"✓ Loaded SARIMAX from {sarimax_path}")
        
        logger.info("All artifacts loaded successfully")
    
    def get_model(self, name: str):
        """Get loaded model by name."""
        return self.models.get(name)
    
    def get_scaler(self, name: str):
        """Get loaded scaler by name."""
        return self.scalers.get(name)
    
    def get_metadata(self, key: str):
        """Get metadata by key."""
        return self.metadata.get(key)
    
    def get_manifest(self) -> Dict[str, Any]:
        """Get full manifest."""
        return self.manifest
    
    @property
    def xgb_model(self):
        """Get SARIMAX baseline model."""
        return self.models.get('xgboost')
    
    @property
    def transformer_model(self):
        """Get Transformer model."""
        return self.models.get('transformer')
    
    @property
    def sarimax_model(self):
        """Get SARIMAX model."""
        return self.models.get('sarimax')
    
    @property
    def feature_order(self):
        """Get feature order list."""
        return self.metadata.get('feature_order', [])
    
    def validate_artifacts(self) -> Dict[str, bool]:
        """
        Validate that all required artifacts exist.
        
        Returns:
            Dictionary of artifact name -> exists
        """
        hourly = self.manifest.get("models", {}).get("hourly", {})
        weekly = self.manifest.get("models", {}).get("weekly", {})
        
        checks = {
            "transformer": (self.base_path / hourly.get("transformer_path", "")).exists(),
            "sarimax_baseline": (self.base_path / hourly.get("baseline_path", "")).exists(),
            "scaler": (self.base_path / hourly.get("scaler_path", "")).exists(),
            "feature_order": (self.base_path / hourly.get("feature_order_path", "")).exists(),
            "residual_stats": (self.base_path / hourly.get("residual_stats_path", "")).exists(),
            "sarimax": (self.base_path / weekly.get("path", "")).exists(),
        }
        
        return checks
    
    def validate_database(self) -> Dict[str, Any]:
        """
        Validate database availability and data sufficiency.
        
        Returns:
            Dictionary with validation results
        """
        from .storage import get_storage_service
        
        try:
            storage = get_storage_service()
            row_count = storage.get_row_count()
            latest_ts = storage.get_latest_timestamp()
            
            # Check if we have at least 168 hours of data
            has_sufficient_data = row_count >= 168
            
            return {
                "available": True,
                "row_count": row_count,
                "latest_timestamp": str(latest_ts) if latest_ts else None,
                "sufficient_for_sequence": has_sufficient_data,
                "min_required": 168
            }
        except Exception as e:
            logger.warning(f"Database validation failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }
