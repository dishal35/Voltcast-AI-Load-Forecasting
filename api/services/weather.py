"""
Weather service for fetching and caching weather forecasts.
Uses OpenWeatherMap API with Redis caching to stay under rate limits.
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import requests

logger = logging.getLogger(__name__)


class WeatherService:
    """Manages weather API calls and caching."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = 'openweathermap',
        coords: str = '28.6139,77.2090',
        redis_client: Optional[Any] = None
    ):
        """
        Initialize weather service.
        
        Args:
            api_key: Weather API key
            provider: Weather provider ('openweathermap')
            coords: Latitude,Longitude string
            redis_client: Redis client for caching (optional)
        """
        self.api_key = api_key or os.getenv('WEATHER_API_KEY')
        self.provider = provider
        
        # Parse coordinates
        lat, lon = coords.split(',')
        self.lat = float(lat)
        self.lon = float(lon)
        
        self.redis_client = redis_client
        
        if not self.api_key:
            logger.warning("No WEATHER_API_KEY provided - will use fallback values")
        
        # Historical averages for fallback (from training data)
        self.historical_averages = self._load_historical_averages()
    
    def _load_historical_averages(self) -> Dict[str, Any]:
        """Load historical averages from final_report.json for fallback."""
        try:
            report_path = os.path.join('artifacts', 'final_report.json')
            if os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    report = json.load(f)
                    return report.get('historical_averages', {})
        except Exception as e:
            logger.warning(f"Could not load historical averages: {e}")
        
        # Default fallback values for Delhi
        return {
            'temperature': 25.0,
            'humidity': 60.0,
            'wind_speed': 3.5,
            'cloud_cover': 40.0,
            'solar_generation_by_hour': {str(h): 100.0 if 6 <= h <= 18 else 0.0 
                                         for h in range(24)}
        }
    
    def get_weather_for_hours(
        self, 
        timestamps: List[datetime],
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get weather data for specific timestamps.
        
        Args:
            timestamps: List of datetime objects
            use_cache: Whether to use Redis cache
        
        Returns:
            List of dicts with keys: ts, temperature, humidity, wind_speed,
                                    cloud_cover, solar_generation
        """
        results = []
        
        for ts in timestamps:
            # Try cache first
            if use_cache and self.redis_client:
                cached = self._get_from_cache(ts)
                if cached:
                    results.append(cached)
                    continue
            
            # Fetch from API or use fallback
            weather = self._fetch_weather_for_timestamp(ts)
            results.append(weather)
            
            # Cache result
            if use_cache and self.redis_client:
                self._store_in_cache(ts, weather)
        
        return results
    
    def _fetch_weather_for_timestamp(self, ts: datetime) -> Dict[str, Any]:
        """Fetch weather for a single timestamp."""
        if not self.api_key:
            logger.debug(f"No API key - using fallback for {ts}")
            return self._get_fallback_weather(ts)
        
        try:
            if self.provider == 'openweathermap':
                return self._fetch_openweathermap(ts)
            else:
                logger.warning(f"Unknown provider {self.provider}, using fallback")
                return self._get_fallback_weather(ts)
        
        except Exception as e:
            logger.error(f"Weather API error for {ts}: {e}")
            return self._get_fallback_weather(ts)
    
    def _fetch_openweathermap(self, ts: datetime) -> Dict[str, Any]:
        """
        Fetch from OpenWeatherMap 5-day/3-hour Forecast API (free tier).
        
        Note: Free tier provides 5-day forecast in 3-hour intervals.
        For timestamps beyond 5 days or in the past, we use fallback.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        # Make ts timezone-aware if it isn't
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hours_ahead = (ts - now).total_seconds() / 3600
        
        # If more than 5 days ahead or in the past, use fallback
        if hours_ahead > 120 or hours_ahead < 0:
            logger.debug(f"Timestamp {ts} is {hours_ahead:.1f}h ahead - using fallback")
            return self._get_fallback_weather(ts)
        
        # Call 5-day/3-hour Forecast API (free tier)
        url = 'https://api.openweathermap.org/data/2.5/forecast'
        params = {
            'lat': self.lat,
            'lon': self.lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Find closest forecast (3-hour intervals)
        forecast_list = data.get('list', [])
        
        closest_forecast = None
        min_diff = float('inf')
        
        from datetime import timezone
        for forecast in forecast_list:
            forecast_ts = datetime.fromtimestamp(forecast['dt'], tz=timezone.utc)
            diff = abs((forecast_ts - ts).total_seconds())
            
            if diff < min_diff:
                min_diff = diff
                closest_forecast = forecast
        
        if not closest_forecast:
            logger.warning(f"No forecast found for {ts}, using fallback")
            return self._get_fallback_weather(ts)
        
        # Extract weather data
        main = closest_forecast.get('main', {})
        wind = closest_forecast.get('wind', {})
        clouds = closest_forecast.get('clouds', {})
        
        temperature = main.get('temp', self.historical_averages.get('temperature', 25.0))
        humidity = main.get('humidity', self.historical_averages.get('humidity', 60.0))
        wind_speed = wind.get('speed', self.historical_averages.get('wind_speed', 3.5))
        cloud_cover = clouds.get('all', self.historical_averages.get('cloud_cover', 40.0))
        
        # Estimate solar generation
        solar_generation = self._estimate_solar_generation(
            cloud_cover, 
            ts.hour,
            temperature
        )
        
        return {
            'ts': ts,
            'temperature': temperature,
            'humidity': humidity,
            'wind_speed': wind_speed,
            'cloud_cover': cloud_cover,
            'solar_generation': solar_generation,
            'source': 'openweathermap'
        }
    
    def _estimate_solar_generation(
        self, 
        cloud_cover_pct: float, 
        hour_of_day: int,
        temperature: float
    ) -> float:
        """
        Estimate solar generation using cloud cover and time of day.
        
        Simple physics-based model:
        - No generation at night (before 6am, after 6pm)
        - Clear sky factor based on cloud cover
        - Temperature efficiency factor
        """
        # Night time
        if hour_of_day < 6 or hour_of_day > 18:
            return 0.0
        
        # Get historical average for this hour
        solar_by_hour = self.historical_averages.get('solar_generation_by_hour', {})
        base_generation = solar_by_hour.get(str(hour_of_day), 100.0)
        
        # Clear sky factor (0-1)
        clear_sky_factor = 1.0 - (cloud_cover_pct / 100.0)
        
        # Temperature efficiency (solar panels less efficient when hot)
        # Optimal around 25°C, loses ~0.5% per degree above
        temp_efficiency = 1.0 - max(0, (temperature - 25) * 0.005)
        temp_efficiency = max(0.7, min(1.0, temp_efficiency))
        
        # Combined estimate
        solar_generation = base_generation * clear_sky_factor * temp_efficiency * 0.9
        
        return max(0.0, solar_generation)
    
    def _get_fallback_weather(self, ts: datetime) -> Dict[str, Any]:
        """Get fallback weather based on historical averages."""
        hour = ts.hour
        month = ts.month
        
        # Seasonal temperature adjustment for Delhi
        seasonal_temp_adj = {
            1: -5, 2: -3, 3: 0, 4: 5, 5: 10, 6: 12,
            7: 8, 8: 6, 9: 4, 10: 2, 11: -2, 12: -5
        }
        
        base_temp = self.historical_averages.get('temperature', 25.0)
        temperature = base_temp + seasonal_temp_adj.get(month, 0)
        
        # Solar generation by hour
        solar_by_hour = self.historical_averages.get('solar_generation_by_hour', {})
        solar_generation = solar_by_hour.get(str(hour), 0.0)
        
        return {
            'ts': ts,
            'temperature': temperature,
            'humidity': self.historical_averages.get('humidity', 60.0),
            'wind_speed': self.historical_averages.get('wind_speed', 3.5),
            'cloud_cover': self.historical_averages.get('cloud_cover', 40.0),
            'solar_generation': solar_generation,
            'source': 'fallback'
        }
    
    def _get_cache_key(self, ts: datetime) -> str:
        """Generate Redis cache key for timestamp."""
        return f"weather:hourly:{ts.strftime('%Y-%m-%dT%H')}"
    
    def _get_from_cache(self, ts: datetime) -> Optional[Dict[str, Any]]:
        """Retrieve weather from Redis cache."""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_cache_key(ts)
            cached = self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                data['ts'] = datetime.fromisoformat(data['ts'])
                logger.debug(f"Cache hit for {ts}")
                return data
        
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    def _store_in_cache(self, ts: datetime, weather: Dict[str, Any]):
        """Store weather in Redis cache."""
        if not self.redis_client:
            return
        
        try:
            key = self._get_cache_key(ts)
            
            # Serialize (convert datetime to ISO string)
            cache_data = weather.copy()
            cache_data['ts'] = cache_data['ts'].isoformat()
            
            # Store with 10 minute TTL
            self.redis_client.setex(
                key,
                600,  # 10 minutes
                json.dumps(cache_data)
            )
            
            logger.debug(f"Cached weather for {ts}")
        
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def fetch_and_cache_forecast(self, hours_ahead: int = 48) -> int:
        """
        Fetch weather forecast for next N hours and cache.
        
        Args:
            hours_ahead: Number of hours to fetch (max 48 for free tier)
        
        Returns:
            Number of hours successfully cached
        """
        now = datetime.utcnow()
        timestamps = [now + timedelta(hours=i) for i in range(1, hours_ahead + 1)]
        
        results = self.get_weather_for_hours(timestamps, use_cache=False)
        
        # Cache all results
        cached_count = 0
        for weather in results:
            if self.redis_client:
                self._store_in_cache(weather['ts'], weather)
                cached_count += 1
        
        logger.info(f"Fetched and cached {cached_count} hours of weather forecast")
        return cached_count


# Global instance
_weather_service: Optional[WeatherService] = None


def get_weather_service(redis_client: Optional[Any] = None) -> WeatherService:
    """Get or create the global weather service instance."""
    global _weather_service
    if _weather_service is None:
        api_key = os.getenv('WEATHER_API_KEY')
        provider = os.getenv('WEATHER_PROVIDER', 'openweathermap')
        coords = os.getenv('WEATHER_COORDS', '28.6139,77.2090')
        
        _weather_service = WeatherService(
            api_key=api_key,
            provider=provider,
            coords=coords,
            redis_client=redis_client
        )
    
    return _weather_service
