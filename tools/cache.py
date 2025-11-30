"""Caching of search results and computations"""

import hashlib
import json
import logging
from typing import Any, Optional, Dict
from functools import wraps
import time

logger = logging.getLogger(__name__)

# In-memory cache (in production can use Redis)
_cache: Dict[str, Dict[str, Any]] = {}


def _make_cache_key(*args, **kwargs) -> str:
    """Creates cache key from arguments."""
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cache_result(ttl: int = 3600):
    """Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{_make_cache_key(*args, **kwargs)}"
            
            if cache_key in _cache:
                cached = _cache[cache_key]
                if time.time() - cached["timestamp"] < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached["value"]
                else:
                    del _cache[cache_key]
            
            result = func(*args, **kwargs)
            
            _cache[cache_key] = {
                "value": result,
                "timestamp": time.time()
            }
            
            logger.debug(f"Cached result for {func.__name__}")
            return result
        
        return wrapper
    return decorator


def clear_cache(pattern: Optional[str] = None):
    """Clears cache.
    
    Args:
        pattern: If specified, clears only keys containing pattern
    """
    if pattern:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]
        logger.info(f"Cleared {len(keys_to_delete)} cache entries matching '{pattern}'")
    else:
        _cache.clear()
        logger.info("Cleared all cache")


def get_cache_stats() -> Dict[str, Any]:
    """Returns cache statistics."""
    now = time.time()
    valid_entries = sum(1 for v in _cache.values() if now - v["timestamp"] < 3600)
    
    return {
        "total_entries": len(_cache),
        "valid_entries": valid_entries,
        "expired_entries": len(_cache) - valid_entries
    }

