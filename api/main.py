"""
Voltcast-AI Load Forecasting API
FastAPI application for hybrid transformer-XGBoost predictions.
Phase 2: Integrated with DB storage and weather service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from .services.model_loader import ModelLoader
from .services.predictor import HybridPredictor
from .routes import predictions, status

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Voltcast-AI Load Forecasting API",
    description="Hybrid Transformer-XGBoost model for electricity demand forecasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    Loads all model artifacts and validates integrity.
    """
    logger.info("=" * 60)
    logger.info("Voltcast-AI Load Forecasting API - Starting Up")
    logger.info("=" * 60)
    
    try:
        # Load manifest and artifacts
        logger.info("Loading model artifacts...")
        model_loader = ModelLoader(manifest_path="artifacts/models/manifest.json")
        model_loader.load_all()
        
        # Validate artifacts
        logger.info("Validating artifacts...")
        artifacts = model_loader.validate_artifacts()
        
        missing = [name for name, exists in artifacts.items() if not exists]
        if missing:
            logger.error(f"Missing artifacts: {missing}")
            raise RuntimeError(f"Missing required artifacts: {missing}")
        
        logger.info("✓ All artifacts validated")
        
        # Initialize predictor (Phase 2: with DB support)
        logger.info("Initializing predictor...")
        use_db = True  # Set to False to use legacy mode
        predictor = HybridPredictor(model_loader, use_db=use_db)
        
        # Set global instances
        predictions.set_predictor(predictor)
        status.set_model_loader(model_loader)
        app.state.storage = predictor.storage_service
        
        # Set model_loader for weekly router
        from .routes import weekly
        weekly.set_model_loader(model_loader)
        
        logger.info(f"✓ Predictor initialized (DB mode: {use_db})")
        
        # Print model info
        manifest = model_loader.get_manifest()
        hourly = manifest.get("models", {}).get("hourly", {})
        metrics = hourly.get("performance_metrics", {}).get("hybrid", {})
        
        logger.info("")
        logger.info("Model Information:")
        logger.info(f"  Name: {hourly.get('name', 'unknown')}")
        logger.info(f"  Features: {hourly.get('n_features', 0)}")
        logger.info(f"  Sequence Length: {hourly.get('seq_len', 0)} hours")
        logger.info(f"  Horizon: {hourly.get('horizon', 0)} hours")
        logger.info(f"  Test MAE: {metrics.get('mae', 0):.4f} MW")
        logger.info(f"  Test RMSE: {metrics.get('rmse', 0):.4f} MW")
        
        residual_stats = model_loader.get_metadata('residual_stats') or {}
        logger.info("")
        logger.info("Residual Statistics:")
        logger.info(f"  Mean: {residual_stats.get('mean', 0):.4f} MW")
        logger.info(f"  Std: {residual_stats.get('std', 0):.4f} MW")
        logger.info(f"  Samples: {residual_stats.get('n', 0):,}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ API Ready - Listening for requests")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down Voltcast-AI API...")


# Include routers
app.include_router(predictions.router)
app.include_router(status.router)

# Import and include weekly router (model_loader set in startup_event)
from .routes import weekly
app.include_router(weekly.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Voltcast-AI Load Forecasting API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "predict": "/api/v1/predict",
            "predict_horizon": "/api/v1/predict/horizon",
            "status": "/api/v1/status",
            "health": "/api/v1/health",
            "docs": "/docs"
        }
    }
