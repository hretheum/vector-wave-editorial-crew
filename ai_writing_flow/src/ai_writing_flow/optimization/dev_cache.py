"""
Development Cache System - Task 11.2

Implements caching for faster local development including:
- Knowledge Base query caching
- Model response caching
- File content caching
- Hot reload cache invalidation
"""

import time
import json
import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import structlog

from ..config.dev_config import get_dev_config

logger = structlog.get_logger(__name__)


class DevelopmentCache:
    """
    Cache system optimized for local development.
    
    Features:
    - Memory and disk caching
    - TTL support
    - Hot reload aware
    - Selective invalidation
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize development cache"""
        config = get_dev_config()
        self.enabled = config.enable_cache
        self.ttl = config.cache_ttl_seconds
        self.cache_dir = Path(cache_dir or config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast access
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Track file modification times for hot reload
        self._file_mtimes: Dict[str, float] = {}
        
        logger.info(
            "Development cache initialized",
            enabled=self.enabled,
            cache_dir=str(self.cache_dir),
            ttl=self.ttl
        )
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create string representation
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        # Hash for consistent key
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() < entry['expires']:
                logger.debug(f"Cache hit (memory): {key}")
                return entry['value']
            else:
                # Expired
                del self._memory_cache[key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if time.time() < entry['expires']:
                    # Load to memory cache
                    self._memory_cache[key] = entry
                    logger.debug(f"Cache hit (disk): {key}")
                    return entry['value']
                else:
                    # Expired
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        if not self.enabled:
            return
        
        expires = time.time() + (ttl or self.ttl)
        entry = {
            'value': value,
            'expires': expires,
            'created': time.time()
        }
        
        # Store in memory
        self._memory_cache[key] = entry
        
        # Store on disk
        cache_file = self.cache_dir / f"{key}.cache"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            logger.debug(f"Cache set: {key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries"""
        if pattern:
            # Invalidate matching keys
            memory_keys = [k for k in self._memory_cache.keys() if pattern in k]
            for key in memory_keys:
                del self._memory_cache[key]
            
            # Disk cache
            for cache_file in self.cache_dir.glob(f"*{pattern}*.cache"):
                cache_file.unlink()
            
            logger.info(f"Invalidated cache pattern: {pattern}")
        else:
            # Clear all
            self._memory_cache.clear()
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            logger.info("Cleared all cache")
    
    def check_file_changes(self, *files: str) -> bool:
        """Check if any tracked files have changed"""
        changed = False
        for file_path in files:
            if Path(file_path).exists():
                mtime = Path(file_path).stat().st_mtime
                if file_path in self._file_mtimes:
                    if mtime > self._file_mtimes[file_path]:
                        changed = True
                self._file_mtimes[file_path] = mtime
        
        if changed:
            logger.info("File changes detected, cache may be stale")
        
        return changed


# Global cache instance
_dev_cache: Optional[DevelopmentCache] = None

def get_dev_cache() -> DevelopmentCache:
    """Get or create development cache"""
    global _dev_cache
    if _dev_cache is None:
        _dev_cache = DevelopmentCache()
    return _dev_cache


# Decorator for caching function results
def cache_result(prefix: str, ttl: Optional[int] = None, 
                check_files: Optional[List[str]] = None):
    """
    Decorator to cache function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        check_files: Files to check for changes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_dev_cache()
            
            # Check file changes if specified
            if check_files:
                if cache.check_file_changes(*check_files):
                    cache.invalidate(prefix)
            
            # Generate cache key
            key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Specialized cache decorators
def cache_kb_query(ttl: Optional[int] = 3600):
    """Cache Knowledge Base queries"""
    return cache_result("kb_query", ttl)


def cache_model_response(ttl: Optional[int] = 1800):
    """Cache model responses"""
    return cache_result("model_response", ttl)


def cache_validation(ttl: Optional[int] = 300):
    """Cache validation results"""
    return cache_result("validation", ttl)


# Development-specific optimizations
class OptimizedFlow:
    """Base class for optimized flows with caching"""
    
    def __init__(self):
        self.cache = get_dev_cache()
        self.config = get_dev_config()
    
    @cache_kb_query()
    def query_knowledge_base(self, query: str, **kwargs) -> Dict[str, Any]:
        """Cached KB query"""
        # This would be overridden by actual implementation
        logger.info(f"KB query (cached): {query}")
        return {"results": [], "cached": True}
    
    @cache_model_response()
    def generate_content(self, prompt: str, **kwargs) -> str:
        """Cached content generation"""
        # This would be overridden by actual implementation
        logger.info(f"Content generation (cached): {prompt[:50]}...")
        return "Generated content"
    
    @cache_validation()
    def validate_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Cached validation"""
        if self.config.skip_validation:
            logger.info("Validation skipped (dev mode)")
            return {"valid": True, "skipped": True}
        
        # This would be overridden by actual implementation
        logger.info("Content validation (cached)")
        return {"valid": True, "cached": True}


# Hot reload support
class HotReloadManager:
    """Manages hot reload for development"""
    
    def __init__(self):
        self.config = get_dev_config()
        self.cache = get_dev_cache()
        self._watchers: Dict[str, float] = {}
    
    def check_reload_needed(self) -> bool:
        """Check if reload is needed"""
        if not self.config.hot_reload:
            return False
        
        reload_needed = False
        
        for watch_path in self.config.watch_paths:
            path = Path(watch_path)
            if path.exists():
                for file_path in path.rglob("*.py"):
                    # Skip ignored patterns
                    if any(pattern in str(file_path) for pattern in self.config.ignore_patterns):
                        continue
                    
                    mtime = file_path.stat().st_mtime
                    file_str = str(file_path)
                    
                    if file_str in self._watchers:
                        if mtime > self._watchers[file_str]:
                            logger.info(f"File changed: {file_str}")
                            reload_needed = True
                    
                    self._watchers[file_str] = mtime
        
        if reload_needed:
            # Invalidate relevant caches
            self.cache.invalidate()
            logger.info("Hot reload triggered")
        
        return reload_needed


# Performance monitoring for development
class DevPerformanceMonitor:
    """Simple performance monitoring for development"""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
    
    def record_timing(self, operation: str, duration: float):
        """Record operation timing"""
        if operation not in self.timings:
            self.timings[operation] = []
        
        self.timings[operation].append(duration)
        
        # Keep only recent timings
        if len(self.timings[operation]) > 100:
            self.timings[operation] = self.timings[operation][-100:]
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get timing statistics"""
        if operation not in self.timings or not self.timings[operation]:
            return {"avg": 0, "min": 0, "max": 0}
        
        times = self.timings[operation]
        return {
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "count": len(times)
        }
    
    def print_summary(self):
        """Print performance summary"""
        print("\n📊 Development Performance Summary:")
        print("=" * 50)
        
        for operation, times in self.timings.items():
            if times:
                stats = self.get_stats(operation)
                print(f"{operation}:")
                print(f"  Avg: {stats['avg']:.3f}s")
                print(f"  Min: {stats['min']:.3f}s") 
                print(f"  Max: {stats['max']:.3f}s")
                print(f"  Count: {stats['count']}")
        
        print("=" * 50)