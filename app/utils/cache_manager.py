
import json
import redis
from typing import Any, Optional, Dict, List
from datetime import timedelta
import pickle
import logging
import asyncio

logger = logging.getLogger(__name__)

class CacheManager:
    """Manage Redis caching operations"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            serialized_value = pickle.dumps(value)
            return await self.redis.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def get_or_set(self, key: str, fetch_func, ttl: int = 3600, *args, **kwargs) -> Any:
        """Get from cache or fetch and set if not exists"""
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Fetch new value
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                new_value = await fetch_func(*args, **kwargs)
            else:
                new_value = fetch_func(*args, **kwargs)
            
            await self.set(key, new_value, ttl)
            return new_value
        except Exception as e:
            logger.error(f"Error fetching data for cache key {key}: {e}")
            return None
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache pattern invalidation error for {pattern}: {e}")
            return 0


