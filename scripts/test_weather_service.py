"""Test weather service with OpenWeatherMap API"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from api.services.weather import WeatherService
import os

print("="*80)
print("Testing Weather Service")
print("="*80)

# Initialize service
api_key = os.getenv('WEATHER_API_KEY', '55280dabecc773bb1cbafa089c067fe2')
weather_service = WeatherService(
    api_key=api_key,
    provider='openweathermap',
    coords='28.6139,77.2090'
)

print(f"\n✓ Weather service initialized")
print(f"  Provider: openweathermap")
print(f"  Coordinates: 28.6139°N, 77.2090°E (Delhi)")
print(f"  API Key: {api_key[:10]}...")

# Test fetching weather for next 3 hours
print(f"\nFetching weather for next 3 hours...")
now = datetime.utcnow()
timestamps = [now + timedelta(hours=i) for i in range(1, 4)]

try:
    weather_data = weather_service.get_weather_for_hours(timestamps, use_cache=False)
    
    print(f"\n✓ Successfully fetched {len(weather_data)} forecasts:")
    for i, w in enumerate(weather_data, 1):
        print(f"\n  Hour {i} ({w['ts'].strftime('%Y-%m-%d %H:%M')}):")
        print(f"    Temperature: {w['temperature']:.1f}°C")
        print(f"    Humidity: {w['humidity']:.0f}%")
        print(f"    Cloud cover: {w['cloud_cover']:.0f}%")
        print(f"    Wind speed: {w['wind_speed']:.1f} m/s")
        print(f"    Solar generation: {w['solar_generation']:.1f} MW")
        print(f"    Source: {w['source']}")
    
    # Check if we got real data or fallback
    sources = [w['source'] for w in weather_data]
    if 'openweathermap' in sources:
        print(f"\n✅ SUCCESS: Weather API is working!")
        print(f"   Got {sources.count('openweathermap')} real forecasts from OpenWeatherMap")
    else:
        print(f"\n⚠️  WARNING: All forecasts are from fallback")
        print(f"   Check API key or network connection")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    print(f"   Using fallback weather data")
    
    # Try fallback
    weather_data = [weather_service._get_fallback_weather(ts) for ts in timestamps]
    print(f"\n✓ Fallback weather data:")
    for i, w in enumerate(weather_data, 1):
        print(f"  Hour {i}: Temp={w['temperature']:.1f}°C, Solar={w['solar_generation']:.1f}MW")

print("\n" + "="*80)
