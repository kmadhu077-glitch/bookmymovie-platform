#!/usr/bin/env python3
"""
Enhanced Caching Layer for BookMyMovie Platform
Provides Redis-compatible caching with fallback to in-memory storage
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
import redis
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """High-performance caching manager with Redis fallback"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = None
        self.in_memory_cache = {}
        self.cache_expiry = {}
        self.cache_stats = defaultdict(int)
        self.lock = threading.RLock()
        
        # Try to connect to Redis
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Connected to Redis server")
            self.backend = "redis"
        except Exception as e:
            logger.warning(f"⚠️  Redis not available, using in-memory cache: {e}")
            self.backend = "memory"
            
        # Start cleanup thread for in-memory cache
        if self.backend == "memory":
            self.cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
            self.cleanup_thread.start()
    
    def _cleanup_expired(self):
        """Clean up expired keys in in-memory cache"""
        while True:
            try:
                current_time = time.time()
                with self.lock:
                    expired_keys = [
                        key for key, expiry in self.cache_expiry.items()
                        if expiry < current_time
                    ]
                    
                    for key in expired_keys:
                        if key in self.in_memory_cache:
                            del self.in_memory_cache[key]
                        del self.cache_expiry[key]
                        self.cache_stats['expired'] += 1
                
                time.sleep(30)  # Cleanup every 30 seconds
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                time.sleep(60)
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set a cached value with expiration"""
        try:
            if self.backend == "redis":
                serialized = json.dumps(value) if not isinstance(value, str) else value
                result = self.redis_client.setex(key, expire, serialized)
                self.cache_stats['redis_sets'] += 1
                return result
            else:
                with self.lock:
                    self.in_memory_cache[key] = value
                    self.cache_expiry[key] = time.time() + expire
                    self.cache_stats['memory_sets'] += 1
                    return True
                    
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cached value"""
        try:
            if self.backend == "redis":
                value = self.redis_client.get(key)
                if value is not None:
                    self.cache_stats['redis_hits'] += 1
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
                else:
                    self.cache_stats['redis_misses'] += 1
                    return None
            else:
                with self.lock:
                    if key in self.in_memory_cache:
                        if key in self.cache_expiry and self.cache_expiry[key] < time.time():
                            # Expired
                            del self.in_memory_cache[key]
                            del self.cache_expiry[key]
                            self.cache_stats['memory_misses'] += 1
                            return None
                        else:
                            self.cache_stats['memory_hits'] += 1
                            return self.in_memory_cache[key]
                    else:
                        self.cache_stats['memory_misses'] += 1
                        return None
                        
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a cached value"""
        try:
            if self.backend == "redis":
                result = self.redis_client.delete(key)
                self.cache_stats['redis_deletes'] += 1
                return bool(result)
            else:
                with self.lock:
                    deleted = key in self.in_memory_cache
                    if deleted:
                        del self.in_memory_cache[key]
                        if key in self.cache_expiry:
                            del self.cache_expiry[key]
                        self.cache_stats['memory_deletes'] += 1
                    return deleted
                    
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.backend == "redis":
                return bool(self.redis_client.exists(key))
            else:
                with self.lock:
                    if key in self.in_memory_cache:
                        if key in self.cache_expiry and self.cache_expiry[key] < time.time():
                            # Expired
                            del self.in_memory_cache[key]
                            del self.cache_expiry[key]
                            return False
                        return True
                    return False
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in cache"""
        try:
            if self.backend == "redis":
                return self.redis_client.incr(key, amount)
            else:
                with self.lock:
                    current = self.get(key) or 0
                    new_value = int(current) + amount
                    self.set(key, new_value)
                    return new_value
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for existing key"""
        try:
            if self.backend == "redis":
                return bool(self.redis_client.expire(key, seconds))
            else:
                with self.lock:
                    if key in self.in_memory_cache:
                        self.cache_expiry[key] = time.time() + seconds
                        return True
                    return False
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = dict(self.cache_stats)
        stats['backend'] = self.backend
        stats['total_keys'] = len(self.in_memory_cache) if self.backend == "memory" else "N/A"
        
        if self.backend == "redis":
            try:
                info = self.redis_client.info()
                stats['redis_memory'] = info.get('used_memory_human', 'N/A')
                stats['redis_connected_clients'] = info.get('connected_clients', 'N/A')
            except:
                pass
                
        return stats
    
    def flush(self) -> bool:
        """Clear all cache"""
        try:
            if self.backend == "redis":
                self.redis_client.flushdb()
            else:
                with self.lock:
                    self.in_memory_cache.clear()
                    self.cache_expiry.clear()
            
            self.cache_stats['flushes'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

# Global cache instance
cache_manager = CacheManager()

# Caching decorators
def cache_result(key_prefix: str, expire: int = 3600):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, expire)
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Invalidate cache keys matching pattern (for in-memory cache)"""
    if cache_manager.backend == "memory":
        with cache_manager.lock:
            keys_to_delete = [
                key for key in cache_manager.in_memory_cache.keys()
                if pattern in key
            ]
            for key in keys_to_delete:
                cache_manager.delete(key)
    else:
        # For Redis, we'd need to implement pattern deletion
        logger.warning("Pattern invalidation not implemented for Redis backend")

# Session management
class SessionManager:
    """Enhanced session management with caching"""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.session_prefix = "session"
        self.default_expire = 1800  # 30 minutes
    
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create a new session"""
        import secrets
        session_id = secrets.token_urlsafe(32)
        session_key = f"{self.session_prefix}:{session_id}"
        
        session_info = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat(),
            **session_data
        }
        
        self.cache.set(session_key, session_info, self.default_expire)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = f"{self.session_prefix}:{session_id}"
        return self.cache.get(session_key)
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data"""
        session_key = f"{self.session_prefix}:{session_id}"
        session = self.get_session(session_id)
        
        if session:
            session.update(data)
            session['last_activity'] = datetime.utcnow().isoformat()
            return self.cache.set(session_key, session, self.default_expire)
        
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        session_key = f"{self.session_prefix}:{session_id}"
        return self.cache.delete(session_key)
    
    def extend_session(self, session_id: str, expire: int = None) -> bool:
        """Extend session expiration"""
        session_key = f"{self.session_prefix}:{session_id}"
        expire = expire or self.default_expire
        return self.cache.expire(session_key, expire)

# Global session manager
session_manager = SessionManager(cache_manager)

# Rate limiting with caching
class RateLimiter:
    """Enhanced rate limiter using cache backend"""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
    
    def is_allowed(self, identifier: str, limit: int, window: int = 3600) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        key = f"rate_limit:{identifier}:{window}"
        
        current_count = self.cache.get(key) or 0
        
        if current_count >= limit:
            return False, {
                'allowed': False,
                'current': current_count,
                'limit': limit,
                'window': window,
                'retry_after': window
            }
        
        # Increment counter
        new_count = self.cache.increment(key)
        if new_count == 1:
            # First request in window, set expiration
            self.cache.expire(key, window)
        
        return True, {
            'allowed': True,
            'current': new_count,
            'limit': limit,
            'window': window,
            'remaining': limit - new_count
        }

# Global rate limiter
rate_limiter = RateLimiter(cache_manager)

if __name__ == "__main__":
    # Test the caching system
    print("🚀 Testing Enhanced Caching Layer")
    print("=" * 40)
    
    # Test basic operations
    cache_manager.set("test_key", {"data": "test_value"}, 60)
    result = cache_manager.get("test_key")
    print(f"✅ Cache test: {result}")
    
    # Test rate limiting
    allowed, info = rate_limiter.is_allowed("test_user", 5, 60)
    print(f"✅ Rate limit test: {allowed}, {info}")
    
    # Test session management
    session_id = session_manager.create_session("user123", {"role": "user"})
    session = session_manager.get_session(session_id)
    print(f"✅ Session test: {session}")
    
    # Show stats
    stats = cache_manager.get_stats()
    print(f"📊 Cache stats: {stats}")
    
    print("\n🎉 Caching layer ready for integration!")