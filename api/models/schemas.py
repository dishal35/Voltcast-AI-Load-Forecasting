"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class PredictionRequest(BaseModel):
    """Request model for single prediction."""
    timestamp: datetime = Field(..., description="Datetime for prediction")
    temperature: Optional[float] = Field(None, description="Temperature in °C (auto-fetched if not provided)", ge=-50, le=60)
    solar_generation: Optional[float] = Field(None, description="Solar generation in MW (auto-fetched if not provided)", ge=0)
    humidity: Optional[float] = Field(None, description="Humidity percentage", ge=0, le=100)
    cloud_cover: Optional[float] = Field(None, description="Cloud cover percentage", ge=0, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2023-01-07T15:00:00",
                "temperature": 25.5,
                "solar_generation": 150.0,
                "humidity": 65.0,
                "cloud_cover": 30.0
            }
        }


class ConfidenceInterval(BaseModel):
    """Confidence interval model."""
    lower: float = Field(..., description="Lower bound (95% CI)")
    upper: float = Field(..., description="Upper bound (95% CI)")
    margin: float = Field(..., description="Margin (±)")


class PredictionComponents(BaseModel):
    """Prediction components model."""
    baseline: float = Field(..., description="XGBoost baseline prediction (MW)")
    residual: float = Field(..., description="Transformer residual correction (MW)")


class PredictionResponse(BaseModel):
    """Response model for single prediction."""
    timestamp: str = Field(..., description="Prediction timestamp (ISO format)")
    prediction: float = Field(..., description="Hybrid prediction (MW)")
    confidence_interval: ConfidenceInterval
    components: Optional[PredictionComponents] = None
    metadata: Optional[Dict[str, Any]] = Field(None, description="Prediction metadata")


class HorizonPredictionRequest(BaseModel):
    """Request model for horizon prediction."""
    timestamp: datetime = Field(..., description="Starting datetime")
    temperature: Optional[float] = Field(None, description="Temperature in °C (auto-fetched if not provided)", ge=-50, le=60)
    solar_generation: Optional[float] = Field(None, description="Solar generation in MW (auto-fetched if not provided)", ge=0)
    humidity: Optional[float] = Field(None, description="Humidity percentage", ge=0, le=100)
    cloud_cover: Optional[float] = Field(None, description="Cloud cover percentage", ge=0, le=100)
    horizon: int = Field(24, description="Number of hours to predict", ge=1, le=168)


class HorizonPredictionResponse(BaseModel):
    """Response model for horizon prediction."""
    timestamp: str = Field(..., description="Starting timestamp (ISO format)")
    horizon: int = Field(..., description="Number of hours predicted")
    predictions: List[float] = Field(..., description="Hybrid predictions for each hour (MW)")
    confidence_intervals: List[ConfidenceInterval] = Field(..., description="Confidence intervals for each hour")
    baselines: List[float] = Field(..., description="XGBoost baselines for each hour (MW)")
    residuals: List[float] = Field(..., description="Transformer residuals for each hour (MW)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Prediction metadata")


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Model version")
    artifacts: Dict[str, bool] = Field(..., description="Artifact availability")
    model_info: Dict[str, Any] = Field(..., description="Model metadata")
    residual_stats: Dict[str, float] = Field(..., description="Residual statistics")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Check timestamp")


class WeeklyForecastRequest(BaseModel):
    """Request model for weekly forecast."""
    start_date: Optional[datetime] = Field(None, description="Start date (defaults to tomorrow)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2023-01-08T00:00:00"
            }
        }


class DailyForecast(BaseModel):
    """Daily forecast summary."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    avg_demand_mw: float = Field(..., description="Average demand (MW)")
    peak_demand_mw: float = Field(..., description="Peak demand (MW)")
    min_demand_mw: float = Field(..., description="Minimum demand (MW)")
    total_energy_mwh: float = Field(..., description="Total energy (MWh)")
    confidence_interval: Optional[Dict[str, float]] = Field(None, description="95% CI bounds")


class WeeklySummary(BaseModel):
    """Weekly summary statistics."""
    avg_demand_mw: float = Field(..., description="Weekly average demand (MW)")
    total_energy_mwh: float = Field(..., description="Total weekly energy (MWh)")
    peak_day: str = Field(..., description="Day with highest average demand")
    peak_demand_mw: float = Field(..., description="Highest daily average (MW)")


class WeeklyForecastResponse(BaseModel):
    """Response model for weekly forecast."""
    forecast_type: str = Field("weekly", description="Forecast type")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    daily_forecasts: List[DailyForecast] = Field(..., description="7-day daily forecasts")
    weekly_summary: WeeklySummary = Field(..., description="Weekly summary")
    model: str = Field("sarimax_daily", description="Model used")
    generated_at: str = Field(..., description="Generation timestamp")
