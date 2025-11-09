"""
Caching service for forecast results.
Uses Redis for fast lookups and TTL-based expiration.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """Manages forecast caching with Redis."""
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize cache service.
        
        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis_client = redis_client
        
        if redis_client is None:
            logger.warning("No Redis client provided - caching disabled")
    
    def get_forecast(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached forecast.
        
        Args:
            key: Cache key
        
        Returns:
            Cached forecast data or None if not found/expired
        """
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(key)
            if cached:
                logger.debug(f"Cache hit: {key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval error for {key}: {e}")
        
        return None
    
    def store_forecast(
        self, 
        key: str, 
        payload: Dict[str, Any], 
        ttl_seconds: int
    ):
        """
        Store forecast in cache.
        
        Args:
            key: Cache key
            payload: Forecast data to cache
            ttl_seconds: Time-to-live in seconds
        """
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(payload, default=str)  # default=str handles datetime
            )
            logger.debug(f"Cached forecast: {key} (TTL: {ttl_seconds}s)")
        except Exception as e:
            logger.warning(f"Cache storage error for {key}: {e}")
    
    def build_forecast_key(
        self,
        forecast_type: str,
        timestamp: datetime,
        history_hash: str
    ) -> str:
        """
        Build cache key for forecast.
        
        Args:
            forecast_type: 'hourly' or 'weekly'
            timestamp: Forecast timestamp
            history_hash: Hash of historical data used
        
        Returns:
            Cache key string
        """
        ts_str = timestamp.strftime('%Y-%m-%dT%H:%M')
        return f"forecast:{forecast_type}:{ts_str}:{history_hash[:8]}"
    
    def compute_history_hash(self, demand_values: list) -> str:
        """
        Compute hash of historical demand values.
        
        Args:
            demand_values: List of recent demand values
        
        Returns:
            SHA256 hash string
        """
        # Convert to string and hash
        data_str = ','.join(f"{v:.2f}" for v in demand_values)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., 'forecast:hourly:*')
        
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache keys matching {pattern}")
                return deleted
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
        
        return 0


# Global instance
_cache_service: Optional[CacheService] = None


def get_cache_service(redis_client: Optional[Any] = None) -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(redis_client)
    return _cache_service


def get_redis_client() -> Optional[Any]:
    """
    Get Redis client if available.
    
    Returns:
        Redis client or None if not configured
    """
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        logger.info("REDIS_URL not set - caching disabled")
        return None
    
    try:
        import redis
        client = redis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        client.ping()
        logger.info(f"Redis connected: {redis_url}")
        return client
    
    except ImportError:
        logger.warning("redis package not installed - caching disabled")
        return None
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} - caching disabled")
        return None
