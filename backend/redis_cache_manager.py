"""
Redis Caching Layer with Advanced Features
High-performance caching with intelligent cache strategies
"""

import redis
import asyncio
import json
import pickle
import hashlib
import logging
from typing import Any, Dict, Optional, List, Union, Callable
from datetime import datetime, timedelta
import time
from dataclasses import dataclass, asdict
from functools import wraps
import os
import threading

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Redis cache configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30

@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    average_get_time: float = 0.0
    average_set_time: float = 0.0
    memory_usage: int = 0
    connected_clients: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

class RedisCache:
    """Advanced Redis caching layer"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.metrics = CacheMetrics()
        self._redis_pool = None
        self._redis_client = None
        self._lock = threading.Lock()
        self._initialized = False
        
        # Cache strategies
        self.strategies = {
            'LRU': 'allkeys-lru',
            'LFU': 'allkeys-lfu', 
            'TTL': 'volatile-ttl',
            'RANDOM': 'allkeys-random'
        }
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        if self._initialized:
            return
            
        try:
            # Create connection pool
            self._redis_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=True
            )
            
            # Create Redis client
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
            
            # Test connection
            await asyncio.to_thread(self._redis_client.ping)
            
            # Configure cache eviction policy
            await asyncio.to_thread(
                self._redis_client.config_set, 
                'maxmemory-policy', 
                self.strategies['LRU']
            )
            
            self._initialized = True
            logger.info(f"Redis cache initialized on {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            # Fallback to in-memory cache
            self._redis_client = None
            raise
    
    def _get_key(self, key: str, namespace: str = None) -> str:
        """Generate namespaced cache key"""
        if namespace:
            return f"bookmymovie:{namespace}:{key}"
        return f"bookmymovie:{key}"
    
    async def get(self, key: str, namespace: str = None) -> Optional[Any]:
        """Get value from cache"""
        start_time = time.time()
        
        try:
            cache_key = self._get_key(key, namespace)
            
            if self._redis_client:
                value = await asyncio.to_thread(self._redis_client.get, cache_key)
                
                if value is not None:
                    # Try to deserialize as JSON first, then pickle
                    try:
                        result = json.loads(value)
                    except json.JSONDecodeError:
                        try:
                            result = pickle.loads(value.encode('latin1'))
                        except:
                            result = value
                    
                    self.metrics.hits += 1
                    return result
                else:
                    self.metrics.misses += 1
                    return None
            else:
                # Fallback in-memory cache (if Redis unavailable)
                return self._memory_cache.get(cache_key) if hasattr(self, '_memory_cache') else None
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics.errors += 1
            return None
        finally:
            # Update metrics
            get_time = time.time() - start_time
            self.metrics.average_get_time = (
                (self.metrics.average_get_time * 0.9) + (get_time * 0.1)
            )
    
    async def set(self, key: str, value: Any, ttl: int = 3600, namespace: str = None) -> bool:
        """Set value in cache"""
        start_time = time.time()
        
        try:
            cache_key = self._get_key(key, namespace)
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                try:
                    serialized_value = json.dumps(value)
                except (TypeError, ValueError):
                    # Fallback to pickle for complex objects
                    serialized_value = pickle.dumps(value).decode('latin1')
            
            if self._redis_client:
                result = await asyncio.to_thread(
                    self._redis_client.setex, 
                    cache_key, 
                    ttl, 
                    serialized_value
                )
                
                if result:
                    self.metrics.sets += 1
                    return True
                    
            else:
                # Fallback in-memory cache
                if not hasattr(self, '_memory_cache'):
                    self._memory_cache = {}
                self._memory_cache[cache_key] = value
                return True
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.metrics.errors += 1
            
        finally:
            # Update metrics
            set_time = time.time() - start_time
            self.metrics.average_set_time = (
                (self.metrics.average_set_time * 0.9) + (set_time * 0.1)
            )
        
        return False
    
    async def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache"""
        try:
            cache_key = self._get_key(key, namespace)
            
            if self._redis_client:
                result = await asyncio.to_thread(self._redis_client.delete, cache_key)
                if result:
                    self.metrics.deletes += 1
                    return True
            else:
                # Fallback in-memory cache
                if hasattr(self, '_memory_cache') and cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    self.metrics.deletes += 1
                    return True
                    
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.metrics.errors += 1
            
        return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace"""
        try:
            if self._redis_client:
                pattern = self._get_key("*", namespace)
                keys = await asyncio.to_thread(self._redis_client.keys, pattern)
                
                if keys:
                    deleted = await asyncio.to_thread(self._redis_client.delete, *keys)
                    self.metrics.deletes += deleted
                    return deleted
                    
        except Exception as e:
            logger.error(f"Cache clear namespace error: {e}")
            self.metrics.errors += 1
            
        return 0
    
    async def increment(self, key: str, amount: int = 1, namespace: str = None, ttl: int = 3600) -> Optional[int]:
        """Increment counter in cache"""
        try:
            cache_key = self._get_key(key, namespace)
            
            if self._redis_client:
                # Use Redis INCR for atomic operations
                value = await asyncio.to_thread(self._redis_client.incr, cache_key, amount)
                
                # Set TTL if this is a new key
                if value == amount:  # New key
                    await asyncio.to_thread(self._redis_client.expire, cache_key, ttl)
                
                return value
                
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            self.metrics.errors += 1
            
        return None
    
    async def get_multiple(self, keys: List[str], namespace: str = None) -> Dict[str, Any]:
        """Get multiple values at once"""
        try:
            cache_keys = [self._get_key(key, namespace) for key in keys]
            
            if self._redis_client:
                values = await asyncio.to_thread(self._redis_client.mget, cache_keys)
                
                result = {}
                for i, value in enumerate(values):
                    if value is not None:
                        try:
                            result[keys[i]] = json.loads(value)
                        except json.JSONDecodeError:
                            try:
                                result[keys[i]] = pickle.loads(value.encode('latin1'))
                            except:
                                result[keys[i]] = value
                        self.metrics.hits += 1
                    else:
                        self.metrics.misses += 1
                
                return result
                
        except Exception as e:
            logger.error(f"Cache get_multiple error: {e}")
            self.metrics.errors += 1
            
        return {}
    
    async def set_multiple(self, data: Dict[str, Any], ttl: int = 3600, namespace: str = None) -> bool:
        """Set multiple values at once"""
        try:
            if self._redis_client:
                pipe = self._redis_client.pipeline()
                
                for key, value in data.items():
                    cache_key = self._get_key(key, namespace)
                    
                    # Serialize value
                    if isinstance(value, (dict, list)):
                        serialized_value = json.dumps(value, default=str)
                    else:
                        try:
                            serialized_value = json.dumps(value)
                        except (TypeError, ValueError):
                            serialized_value = pickle.dumps(value).decode('latin1')
                    
                    pipe.setex(cache_key, ttl, serialized_value)
                
                results = await asyncio.to_thread(pipe.execute)
                
                if all(results):
                    self.metrics.sets += len(data)
                    return True
                    
        except Exception as e:
            logger.error(f"Cache set_multiple error: {e}")
            self.metrics.errors += 1
            
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "metrics": asdict(self.metrics),
            "connected": self._redis_client is not None,
            "config": asdict(self.config)
        }
        
        if self._redis_client:
            try:
                info = await asyncio.to_thread(self._redis_client.info)
                stats.update({
                    "redis_version": info.get("redis_version"),
                    "used_memory": info.get("used_memory"),
                    "used_memory_human": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                })
                
                # Update metrics from Redis info
                self.metrics.memory_usage = info.get("used_memory", 0)
                self.metrics.connected_clients = info.get("connected_clients", 0)
                
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats
    
    async def close(self):
        """Close Redis connections"""
        if self._redis_pool:
            self._redis_pool.disconnect()
        logger.info("Redis cache connections closed")

# Cache decorators
def cached(ttl: int = 3600, namespace: str = None, key_func: Callable = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl, namespace)
            
            return result
        return wrapper
    return decorator

def cache_invalidate(namespace: str = None, key: str = None):
    """Decorator for cache invalidation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if key:
                await cache_manager.delete(key, namespace)
            elif namespace:
                await cache_manager.clear_namespace(namespace)
            
            return result
        return wrapper
    return decorator

# Global cache manager
cache_manager: Optional[RedisCache] = None

async def init_cache():
    """Initialize global cache manager"""
    global cache_manager
    
    config = CacheConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD'),
        max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    )
    
    cache_manager = RedisCache(config)
    await cache_manager.initialize()
    
    logger.info("Cache manager initialized")

async def close_cache():
    """Close global cache manager"""
    if cache_manager:
        await cache_manager.close()
    logger.info("Cache manager closed")

# Cache utilities
class CacheKeys:
    """Standard cache key patterns"""
    USER_PROFILE = "user:profile:{user_id}"
    MOVIE_DETAILS = "movie:details:{movie_id}"
    THEATER_LISTINGS = "theater:listings:{theater_id}:{date}"
    SEARCH_RESULTS = "search:movies:{query_hash}"
    RECOMMENDATIONS = "recommendations:{user_id}"
    POPULAR_MOVIES = "movies:popular:{category}"
    BOOKING_SUMMARY = "booking:summary:{booking_id}"
    
    @staticmethod
    def format_key(pattern: str, **kwargs) -> str:
        """Format cache key with parameters"""
        return pattern.format(**kwargs)

# Performance monitoring
class CacheMonitor:
    """Cache performance monitoring"""
    
    @staticmethod
    async def get_performance_report() -> Dict[str, Any]:
        """Generate cache performance report"""
        if not cache_manager:
            return {"error": "Cache manager not initialized"}
        
        stats = await cache_manager.get_stats()
        
        # Calculate performance indicators
        performance_indicators = {
            "cache_efficiency": "excellent" if stats["metrics"]["hit_rate"] > 80 else "good" if stats["metrics"]["hit_rate"] > 60 else "needs_improvement",
            "response_time": "fast" if stats["metrics"]["average_get_time"] < 0.01 else "moderate" if stats["metrics"]["average_get_time"] < 0.05 else "slow",
            "error_rate": (stats["metrics"]["errors"] / max(stats["metrics"]["hits"] + stats["metrics"]["misses"], 1)) * 100,
            "recommendations": []
        }
        
        # Generate recommendations
        if stats["metrics"]["hit_rate"] < 70:
            performance_indicators["recommendations"].append("Consider increasing cache TTL for stable data")
        
        if stats["metrics"]["average_get_time"] > 0.05:
            performance_indicators["recommendations"].append("Check Redis server performance and network latency")
        
        if performance_indicators["error_rate"] > 5:
            performance_indicators["recommendations"].append("Investigate and fix cache connection issues")
        
        return {
            "stats": stats,
            "performance": performance_indicators,
            "timestamp": datetime.now().isoformat()
        }