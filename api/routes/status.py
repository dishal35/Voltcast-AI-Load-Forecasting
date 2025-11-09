"""
Status and health check routes.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from ..models.schemas import StatusResponse, HealthResponse
from ..services.model_loader import ModelLoader

router = APIRouter(prefix="/api/v1", tags=["status"])

# Global model loader instance
_model_loader: ModelLoader = None


def set_model_loader(loader: ModelLoader):
    """Set global model loader instance."""
    global _model_loader
    _model_loader = loader


def get_model_loader() -> ModelLoader:
    """Dependency to get model loader instance."""
    return _model_loader


@router.get("/status", response_model=StatusResponse)
async def get_status(loader: ModelLoader = Depends(get_model_loader)):
    """
    Get service status and model information.
    
    Returns manifest metadata, artifact status, and residual statistics.
    """
    manifest = loader.get_manifest()
    artifacts = loader.validate_artifacts()
    residual_stats = loader.get_metadata('residual_stats') or {}
    
    hourly_config = manifest.get("models", {}).get("hourly", {})
    
    return {
        "status": "operational",
        "version": manifest.get("model_store_version", "1.0"),
        "artifacts": artifacts,
        "model_info": {
            "name": hourly_config.get("name", "hybrid_transformer_xgboost"),
            "seq_len": hourly_config.get("seq_len", 168),
            "horizon": hourly_config.get("horizon", 24),
            "n_features": hourly_config.get("n_features", 59),
            "training_date": hourly_config.get("training_date", "unknown"),
            "metrics": hourly_config.get("performance_metrics", {})
        },
        "residual_stats": {
            "mean": residual_stats.get("mean", 0.0),
            "std": residual_stats.get("std", 3.88),
            "n": residual_stats.get("n", 0)
        }
    }


@router.get("/health")
async def health_check():
    """
    Enhanced health check endpoint (Phase 2).
    
    Checks database, cache, and model availability.
    Returns detailed component status.
    """
    from ..services.storage import get_storage_service
    from ..services.cache import get_redis_client
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        storage = get_storage_service()
        row_count = storage.get_row_count()
        latest_ts = storage.get_latest_timestamp()
        health_status["components"]["database"] = {
            "status": "healthy" if row_count > 0 else "warning",
            "rows": row_count,
            "latest_timestamp": str(latest_ts) if latest_ts else None
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            health_status["components"]["cache"] = {
                "status": "healthy",
                "type": "redis"
            }
        else:
            health_status["components"]["cache"] = {
                "status": "disabled",
                "type": "none"
            }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check models
    try:
        if _model_loader:
            artifacts = _model_loader.validate_artifacts()
            all_present = all(artifacts.values())
            health_status["components"]["models"] = {
                "status": "healthy" if all_present else "degraded",
                "artifacts": artifacts
            }
        else:
            health_status["components"]["models"] = {
                "status": "not_initialized"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["models"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status
