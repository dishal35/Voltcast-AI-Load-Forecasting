-- Delhi Demand Forecasting - Database Schema
-- Phase 2: Historical Data Storage

-- Table: hourly_actuals
-- Stores observed hourly data for feature computation and model training
CREATE TABLE IF NOT EXISTS hourly_actuals (
    ts TIMESTAMP WITHOUT TIME ZONE NOT NULL PRIMARY KEY,
    demand DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    solar_generation DOUBLE PRECISION,
    cloud_cover DOUBLE PRECISION,
    is_holiday BOOLEAN DEFAULT FALSE,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient time-range queries
CREATE INDEX IF NOT EXISTS idx_hourly_actuals_ts ON hourly_actuals(ts DESC);

-- Table: weather_cache
-- Stores fetched weather forecasts to reduce API calls
CREATE TABLE IF NOT EXISTS weather_cache (
    ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    cloud_cover DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    solar_generation_estimate DOUBLE PRECISION,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts, provider)
);

-- Index for weather lookups
CREATE INDEX IF NOT EXISTS idx_weather_cache_ts ON weather_cache(ts);
CREATE INDEX IF NOT EXISTS idx_weather_cache_fetched ON weather_cache(fetched_at DESC);

-- Table: forecast_cache
-- Stores computed forecasts to avoid recomputation
CREATE TABLE IF NOT EXISTS forecast_cache (
    cache_key VARCHAR(255) NOT NULL PRIMARY KEY,
    forecast_type VARCHAR(20) NOT NULL,
    forecast_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Index for cache expiration cleanup
CREATE INDEX IF NOT EXISTS idx_forecast_cache_expires ON forecast_cache(expires_at);

-- Cleanup old cache entries (run periodically)
-- DELETE FROM forecast_cache WHERE expires_at < CURRENT_TIMESTAMP;
-- DELETE FROM weather_cache WHERE fetched_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
