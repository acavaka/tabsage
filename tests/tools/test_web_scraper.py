"""Unit tests for Web Scraper"""

import pytest
from tools.web_scraper import scrape_url


class TestWebScraper:
    """Tests for Web Scraper"""
    
    def test_scrape_url_invalid(self):
        """Test invalid URL processing"""
        result = scrape_url("not-a-url")
        
        assert result is not None
        assert result.get("status") == "error" or "error_message" in result
    
    def test_scrape_url_format(self):
        """Test result format"""
        # Use mock or real URL for test
        # In real test can use pytest-httpx for mocking
        result = scrape_url("https://example.com")
        
        assert result is not None
        assert "status" in result
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "success":
            assert "text" in result
            assert "title" in result

