"""Unit tests for Cache"""

import pytest
import time
from tools.cache import cache_result, clear_cache, get_cache_stats


class TestCache:
    """Tests for caching system"""
    
    def test_cache_result(self):
        """Test function result caching"""
        clear_cache()
        
        call_count = 0
        
        @cache_result(ttl=60)
        def test_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - function executes
        result1 = test_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - result from cache
        result2 = test_function(5)
        assert result2 == 10
        assert call_count == 1  # Function was not called again
    
    def test_cache_ttl_expiry(self):
        """Test cache TTL expiry"""
        clear_cache()
        
        call_count = 0
        
        @cache_result(ttl=1)  # TTL 1 second
        def test_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call
        test_function(5)
        assert call_count == 1
        
        # Second call immediately - from cache
        test_function(5)
        assert call_count == 1
        
        # Wait for TTL expiry
        time.sleep(2)
        
        # Third call - function is called again
        test_function(5)
        assert call_count == 2
    
    def test_clear_cache(self):
        """Test cache clearing"""
        clear_cache()
        
        @cache_result(ttl=60)
        def test_function(x):
            return x * 2
        
        # Cache result
        test_function(5)
        
        # Clear cache
        clear_cache()
        
        # Check statistics
        stats = get_cache_stats()
        assert stats["total_entries"] == 0
    
    def test_get_cache_stats(self):
        """Test cache statistics retrieval"""
        clear_cache()
        
        @cache_result(ttl=60)
        def test_function(x):
            return x * 2
        
        test_function(5)
        test_function(10)
        
        stats = get_cache_stats()
        assert stats["total_entries"] >= 2
        assert stats["valid_entries"] >= 2

