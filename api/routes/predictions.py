"""
Prediction API routes.
Phase 3: Enhanced with rate limiting and improved caching.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime
import logging
from collections import defaultdict
from time import time

from ..models.schemas import (
    PredictionRequest,
    PredictionResponse,
    HorizonPredictionRequest,
    HorizonPredictionResponse
)
from ..services.predictor import HybridPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predictions"])

# Simple in-memory rate limiter (for demo)
# In production, use Redis-based rate limiting
_rate_limit_store = defaultdict(list)
RATE_LIMIT = 60  # requests per minute
RATE_WINDOW = 60  # seconds

# Global predictor instance (set by main app)
_predictor: HybridPredictor = None


def set_predictor(predictor: HybridPredictor):
    """Set global predictor instance."""
    global _predictor
    _predictor = predictor


def get_predictor() -> HybridPredictor:
    """Dependency to get predictor instance."""
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Predictor not initialized")
    return _predictor


def check_rate_limit(request: Request):
    """
    Simple in-memory rate limiter.
    Limits to 60 requests per minute per IP.
    
    In production, use Redis-based rate limiting for distributed systems.
    """
    client_ip = request.client.host if request.client else "unknown"
    current_time = time()
    
    # Clean old entries
    _rate_limit_store[client_ip] = [
        req_time for req_time in _rate_limit_store[client_ip]
        if current_time - req_time < RATE_WINDOW
    ]
    
    # Check limit
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} requests per minute."
        )
    
    # Record request
    _rate_limit_store[client_ip].append(current_time)


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    pred_request: PredictionRequest,
    http_request: Request,
    predictor: HybridPredictor = Depends(get_predictor),
    _: None = Depends(check_rate_limit)
):
    """
    Make a single hybrid prediction.
    
    Phase 3 Enhancements:
    - Rate limited to 60 requests/minute per IP
    - Uses DB-backed feature computation
    - Redis caching with 10-minute TTL
    - Per-hour confidence intervals
    
    Returns baseline + residual correction with 95% confidence intervals.
    Auto-fetches weather if not provided.
    """
    try:
        result = predictor.predict(
            timestamp=pred_request.timestamp,
            temperature=pred_request.temperature,
            solar_generation=pred_request.solar_generation,
            humidity=pred_request.humidity,
            cloud_cover=pred_request.cloud_cover,
            return_components=True,
            use_cache=True
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/predict/horizon", response_model=HorizonPredictionResponse)
async def predict_horizon(
    pred_request: HorizonPredictionRequest,
    http_request: Request,
    predictor: HybridPredictor = Depends(get_predictor),
    _: None = Depends(check_rate_limit)
):
    """
    Make predictions for full horizon (up to 168 hours).
    
    Phase 3 Enhancements:
    - Rate limited to 60 requests/minute per IP
    - Uses DB-backed feature computation
    - Redis caching with 10-minute TTL
    - Per-hour confidence intervals from residual statistics
    
    Auto-fetches weather for each hour if not provided.
    Returns 24-hour (or custom) forecast with confidence intervals.
    """
    try:
        result = predictor.predict_horizon(
            timestamp=pred_request.timestamp,
            temperature=pred_request.temperature,
            solar_generation=pred_request.solar_generation,
            humidity=pred_request.humidity,
            cloud_cover=pred_request.cloud_cover,
            horizon=pred_request.horizon,
            use_cache=True
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Horizon prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Horizon prediction failed: {str(e)}")
