"""
Unit tests for weather service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from api.services.weather import WeatherService


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = Mock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    return redis_mock


def test_weather_service_initialization():
    """Test basic initialization."""
    service = WeatherService(
        api_key='test_key',
        provider='openweathermap',
        coords='28.6139,77.2090'
    )
    
    assert service.api_key == 'test_key'
    assert service.provider == 'openweathermap'
    assert service.lat == 28.6139
    assert service.lon == 77.2090


def test_fallback_weather():
    """Test fallback weather when no API key."""
    service = WeatherService(api_key=None)
    
    ts = datetime(2023, 6, 15, 14, 0)
    weather = service._get_fallback_weather(ts)
    
    assert 'temperature' in weather
    assert 'humidity' in weather
    assert 'solar_generation' in weather
    assert weather['source'] == 'fallback'
    assert weather['ts'] == ts


def test_solar_generation_estimation():
    """Test solar generation estimation logic."""
    service = WeatherService(api_key='test')
    
    # Daytime with clear sky
    solar_day_clear = service._estimate_solar_generation(
        cloud_cover_pct=10,
        hour_of_day=12,
        temperature=25
    )
    assert solar_day_clear > 0
    
    # Daytime with cloudy sky
    solar_day_cloudy = service._estimate_solar_generation(
        cloud_cover_pct=90,
        hour_of_day=12,
        temperature=25
    )
    assert solar_day_cloudy < solar_day_clear
    
    # Night time
    solar_night = service._estimate_solar_generation(
        cloud_cover_pct=10,
        hour_of_day=22,
        temperature=20
    )
    assert solar_night == 0.0


def test_get_weather_for_hours_with_cache(mock_redis):
    """Test weather retrieval with caching."""
    service = WeatherService(
        api_key=None,  # Will use fallback
        redis_client=mock_redis
    )
    
    timestamps = [
        datetime(2023, 6, 15, 12, 0),
        datetime(2023, 6, 15, 13, 0)
    ]
    
    results = service.get_weather_for_hours(timestamps, use_cache=True)
    
    assert len(results) == 2
    assert all('temperature' in r for r in results)
    assert all('solar_generation' in r for r in results)
    
    # Should have attempted to cache
    assert mock_redis.setex.called


def test_get_weather_for_hours_without_cache():
    """Test weather retrieval without caching."""
    service = WeatherService(api_key=None)
    
    timestamps = [datetime(2023, 6, 15, 12, 0)]
    results = service.get_weather_for_hours(timestamps, use_cache=False)
    
    assert len(results) == 1
    assert results[0]['source'] == 'fallback'


@patch('api.services.weather.requests.get')
def test_openweathermap_api_call(mock_get):
    """Test OpenWeatherMap API integration."""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        'hourly': [
            {
                'dt': int(datetime(2023, 6, 15, 12, 0).timestamp()),
                'temp': 30.0,
                'humidity': 65,
                'wind_speed': 4.5,
                'clouds': 25
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    service = WeatherService(api_key='test_key')
    
    ts = datetime.utcnow() + timedelta(hours=1)  # Within 48h
    weather = service._fetch_openweathermap(ts)
    
    assert weather['temperature'] == 30.0
    assert weather['humidity'] == 65
    assert weather['source'] == 'openweathermap'
    assert mock_get.called


def test_cache_key_generation():
    """Test cache key format."""
    service = WeatherService(api_key='test')
    
    ts = datetime(2023, 6, 15, 14, 30)
    key = service._get_cache_key(ts)
    
    assert key == 'weather:hourly:2023-06-15T14'
    assert isinstance(key, str)
