"""
Model Loader Service
Loads and manages ML model artifacts.
"""
import json
import joblib
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class PositionalEncoding(nn.Module):
    """Positional encoding for Transformer."""
    
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        import math
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x):
        seq_len = x.size(1)
        x = x + self.pe[:, :seq_len, :]
        return x


class ResidualTransformer(nn.Module):
    """PyTorch Transformer for residual prediction."""
    
    def __init__(self, d_model=64, nhead=4, num_layers=2, dim_feedforward=128, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(1, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc_out = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, 1)
        )

    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: [batch, seq_len, 1]
        
        Returns:
            [batch] predictions
        """
        x = self.input_proj(x)                # [batch, seq_len, d_model]
        x = self.pos_encoder(x)               # [batch, seq_len, d_model]
        x = self.transformer_encoder(x)       # [batch, seq_len, d_model]
        x = x[:, -1, :]                       # use last token
        out = self.fc_out(x)                  # [batch, 1]
        return out.squeeze(-1)                # [batch]


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
        
        # Load LightGBM baseline
        lgb_path = self.base_path / hourly.get("baseline_path", "")
        if lgb_path.exists():
            import lightgbm as lgb
            self.models['lgbm'] = lgb.Booster(model_file=str(lgb_path))
            logger.info(f"✓ Loaded LightGBM baseline from {lgb_path}")
        else:
            logger.warning(f"LightGBM model not found at {lgb_path}")
        
        # Load PyTorch Transformer
        transformer_path = self.base_path / hourly.get("transformer_path", "")
        if transformer_path.exists():
            try:
                model = ResidualTransformer(
                    d_model=64,
                    nhead=4,
                    num_layers=2,
                    dim_feedforward=128,
                    dropout=0.1
                )
                model.load_state_dict(torch.load(str(transformer_path), map_location='cpu'))
                model.eval()
                self.models['transformer'] = model
                logger.info(f"✓ Loaded PyTorch Transformer from {transformer_path}")
            except Exception as e:
                logger.warning(f"Failed to load Transformer: {e}")
        else:
            logger.warning(f"Transformer model not found at {transformer_path}")
        
        # Load feature scaler (for input features)
        scaler_path = self.base_path / hourly.get("scaler_path", "")
        if scaler_path.exists():
            self.scalers['transformer'] = joblib.load(str(scaler_path))
            logger.info(f"✓ Loaded feature scaler from {scaler_path}")
        
        # Load residual scaler (for residuals)
        res_scaler_path = self.base_path / hourly.get("residual_scaler_path", "")
        if res_scaler_path.exists():
            self.scalers['residual'] = joblib.load(str(res_scaler_path))
            logger.info(f"✓ Loaded residual scaler from {res_scaler_path}")
        else:
            logger.warning(f"Residual scaler not found at {res_scaler_path}")
        
        # Load feature order
        feat_path = self.base_path / hourly.get("feature_order_path", "")
        if feat_path.exists():
            with open(feat_path) as f:
                data = json.load(f)
                self.metadata['feature_order'] = data.get("feature_order", data) if isinstance(data, dict) else data
            logger.info(f"✓ Loaded feature order ({len(self.metadata['feature_order'])} features)")
        else:
            logger.warning(f"Feature order not found at {feat_path}")
        
        # Load residual stats
        stats_path = self.base_path / hourly.get("residual_stats_path", "")
        if stats_path.exists():
            self.metadata['residual_stats'] = joblib.load(str(stats_path))
            logger.info(f"✓ Loaded residual stats")
        else:
            logger.warning(f"Residual stats not found at {stats_path}")
        
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
    def lgbm_model(self):
        """Get LightGBM baseline model."""
        return self.models.get('lgbm')
    
    @property
    def xgb_model(self):
        """Get baseline model (backward compatibility)."""
        return self.models.get('lgbm')
    
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
            "lgbm_baseline": (self.base_path / hourly.get("baseline_path", "")).exists(),
            "scaler": (self.base_path / hourly.get("scaler_path", "")).exists(),
            "residual_scaler": (self.base_path / hourly.get("residual_scaler_path", "")).exists(),
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
