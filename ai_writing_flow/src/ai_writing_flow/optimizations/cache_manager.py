"""
Intelligent Cache Manager - Advanced caching system for performance optimization

This module implements a sophisticated caching layer that reduces redundant
operations and optimizes memory usage for critical flow operations.
"""

import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import RLock
import weakref
import gc
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0
    ttl: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self) -> None:
        """Update access metadata"""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    memory_usage_bytes: int = 0
    total_entries: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate
    
    @property
    def memory_usage_mb(self) -> float:
        """Get memory usage in MB"""
        return self.memory_usage_bytes / (1024 * 1024)


class IntelligentCacheManager:
    """
    Advanced caching system with intelligent eviction and memory management
    
    Features:
    - LRU eviction with frequency weighting
    - Automatic memory management
    - TTL support for time-sensitive data
    - Hierarchical cache levels
    - Memory-efficient serialization
    - Performance monitoring
    """
    
    def __init__(self,
                 max_memory_mb: int = 100,
                 max_entries: int = 1000,
                 default_ttl: Optional[float] = 3600,  # 1 hour
                 cleanup_interval: float = 300):  # 5 minutes
        """
        Initialize IntelligentCacheManager
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            max_entries: Maximum number of cache entries
            default_ttl: Default TTL for cache entries (seconds)
            cleanup_interval: Interval for automatic cleanup (seconds)
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Cache storage with thread safety
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()
        
        # Statistics tracking
        self._stats = CacheStatistics()
        
        # Hierarchical cache levels
        self._l1_cache: Dict[str, Any] = {}  # Hot data (no serialization)
        self._l2_cache: Dict[str, bytes] = {}  # Compressed data
        
        # Automatic cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        logger.info(f"🧠 IntelligentCacheManager initialized: "
                   f"{max_memory_mb}MB, {max_entries} entries, "
                   f"TTL: {default_ttl}s")
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            logger.info("No event loop found, automatic cleanup disabled")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                cleaned = self._cleanup_expired()
                if cleaned > 0:
                    logger.debug(f"🧹 Cleaned up {cleaned} expired cache entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create deterministic key from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of cached value in bytes"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value.encode() if isinstance(value, str) else value)
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, default=str).encode())
            else:
                # Rough estimate for other types
                return len(str(value).encode()) * 2
        except Exception:
            return 1024  # Default estimate
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            self._stats.total_requests += 1
            
            # Check L1 cache first (hot data)
            if key in self._l1_cache:
                self._stats.cache_hits += 1
                return self._l1_cache[key]
            
            # Check main cache
            if key in self._cache:
                entry = self._cache[key]
                
                # Check if expired
                if entry.is_expired():
                    del self._cache[key]
                    self._stats.cache_misses += 1
                    self._stats.evictions += 1
                    return None
                
                # Move to end (LRU)
                self._cache.move_to_end(key)
                entry.touch()
                
                self._stats.cache_hits += 1
                
                # Promote frequently accessed items to L1
                if entry.access_count > 5 and len(self._l1_cache) < 50:
                    self._l1_cache[key] = entry.value
                
                return entry.value
            
            self._stats.cache_misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (optional, uses default if not specified)
        """
        with self._lock:
            current_time = time.time()
            actual_ttl = ttl if ttl is not None else self.default_ttl
            
            # Estimate size
            size_bytes = self._estimate_size(value)
            
            # Check memory limits before adding
            if (self._stats.memory_usage_bytes + size_bytes > self.max_memory_bytes 
                or len(self._cache) >= self.max_entries):
                self._evict_entries(size_bytes)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                last_accessed=current_time,
                size_bytes=size_bytes,
                ttl=actual_ttl
            )
            
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.memory_usage_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = entry
            self._stats.memory_usage_bytes += size_bytes
            self._stats.total_entries = len(self._cache)
            
            # Add to L1 cache if small and likely to be accessed frequently
            if size_bytes < 10240 and len(self._l1_cache) < 50:  # < 10KB
                self._l1_cache[key] = value
    
    def _evict_entries(self, required_bytes: int) -> None:
        """
        Evict entries to free up memory
        
        Args:
            required_bytes: Minimum bytes to free up
        """
        freed_bytes = 0
        evicted_count = 0
        
        # First, remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            entry = self._cache.pop(key)
            freed_bytes += entry.size_bytes
            evicted_count += 1
            
            # Remove from L1 cache too
            self._l1_cache.pop(key, None)
        
        # If still need more space, use LRU with frequency weighting
        while (freed_bytes < required_bytes and self._cache):
            # Find least valuable entry (old + infrequently accessed)
            least_valuable_key = None
            lowest_score = float('inf')
            
            current_time = time.time()
            
            for key, entry in self._cache.items():
                # Score based on recency and frequency
                age_factor = current_time - entry.last_accessed
                frequency_factor = 1.0 / max(1, entry.access_count)
                score = age_factor * frequency_factor
                
                if score < lowest_score:
                    lowest_score = score
                    least_valuable_key = key
            
            if least_valuable_key:
                entry = self._cache.pop(least_valuable_key)
                freed_bytes += entry.size_bytes
                evicted_count += 1
                
                # Remove from L1 cache too
                self._l1_cache.pop(least_valuable_key, None)
        
        # Update statistics
        self._stats.memory_usage_bytes -= freed_bytes
        self._stats.evictions += evicted_count
        self._stats.total_entries = len(self._cache)
        
        logger.debug(f"🗑️ Evicted {evicted_count} entries, freed {freed_bytes/1024:.1f}KB")
    
    def _cleanup_expired(self) -> int:
        """Clean up expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                entry = self._cache.pop(key)
                self._stats.memory_usage_bytes -= entry.size_bytes
                self._l1_cache.pop(key, None)
            
            self._stats.total_entries = len(self._cache)
            return len(expired_keys)
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._stats.memory_usage_bytes -= entry.size_bytes
                self._stats.total_entries = len(self._cache)
                self._l1_cache.pop(key, None)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._l1_cache.clear()
            self._stats.memory_usage_bytes = 0
            self._stats.total_entries = 0
            logger.info("🧹 Cache cleared")
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics"""
        with self._lock:
            return CacheStatistics(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                evictions=self._stats.evictions,
                memory_usage_bytes=self._stats.memory_usage_bytes,
                total_entries=self._stats.total_entries
            )
    
    def cache_function(self, ttl: Optional[float] = None, key_prefix: str = ""):
        """
        Decorator for caching function results
        
        Args:
            ttl: Time to live for cached results
            key_prefix: Prefix for cache keys
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{self._generate_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"💾 Cache hit for {func.__name__}")
                    return cached_result
                
                # Execute function and cache result
                logger.debug(f"🔄 Cache miss for {func.__name__}, executing")
                result = func(*args, **kwargs)
                self.put(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    async def cache_async_function(self, ttl: Optional[float] = None, key_prefix: str = ""):
        """
        Decorator for caching async function results
        
        Args:
            ttl: Time to live for cached results
            key_prefix: Prefix for cache keys
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{self._generate_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"💾 Cache hit for async {func.__name__}")
                    return cached_result
                
                # Execute function and cache result
                logger.debug(f"🔄 Cache miss for async {func.__name__}, executing")
                result = await func(*args, **kwargs)
                self.put(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def shutdown(self) -> None:
        """Shutdown cache manager and cleanup resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        self.clear()
        logger.info("🛑 IntelligentCacheManager shutdown complete")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.shutdown()
        except Exception:
            pass  # Ignore errors during cleanup


# Global cache instance
_global_cache: Optional[IntelligentCacheManager] = None


def get_global_cache() -> IntelligentCacheManager:
    """Get or create global cache instance"""
    global _global_cache
    
    if _global_cache is None:
        _global_cache = IntelligentCacheManager(
            max_memory_mb=50,  # Conservative default
            max_entries=500,
            default_ttl=1800   # 30 minutes
        )
    
    return _global_cache


def cached(ttl: Optional[float] = None, key_prefix: str = ""):
    """
    Convenient decorator for caching function results using global cache
    
    Args:
        ttl: Time to live for cached results
        key_prefix: Prefix for cache keys
    """
    cache = get_global_cache()
    return cache.cache_function(ttl=ttl, key_prefix=key_prefix)


def async_cached(ttl: Optional[float] = None, key_prefix: str = ""):
    """
    Convenient decorator for caching async function results using global cache
    
    Args:
        ttl: Time to live for cached results  
        key_prefix: Prefix for cache keys
    """
    cache = get_global_cache()
    return cache.cache_async_function(ttl=ttl, key_prefix=key_prefix)