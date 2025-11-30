"""Unit tests for Intent Recognition Agent"""

import pytest
import asyncio
from agents.intent_agent import recognize_intent, UserIntent


class TestIntentAgent:
    """Tests for Intent Recognition Agent"""
    
    @pytest.mark.asyncio
    async def test_intent_process_url(self):
        """Test URL processing intent recognition"""
        result = await recognize_intent("https://habr.com/ru/articles/519982/")
        
        assert result is not None
        assert "intent" in result
        assert result["intent"] == UserIntent.PROCESS_URL
        # URL can be in parameters or directly in result
        assert "url" in result.get("parameters", {}) or "url" in result
    
    @pytest.mark.asyncio
    async def test_intent_search(self):
        """Test search intent recognition"""
        result = await recognize_intent("find microservices")
        
        assert result is not None
        assert "intent" in result
        assert result["intent"] == UserIntent.SEARCH_DATABASE
        assert "query" in result.get("parameters", {})
    
    @pytest.mark.asyncio
    async def test_intent_unknown(self):
        """Test unknown intent processing"""
        result = await recognize_intent("hello how are you")
        
        assert result is not None
        assert "intent" in result
        # Can be UNKNOWN or other intent
        assert result["intent"] in [UserIntent.UNKNOWN, UserIntent.SEARCH_DATABASE]
    
    @pytest.mark.asyncio
    async def test_intent_empty_message(self):
        """Test empty message processing"""
        result = await recognize_intent("")
        
        assert result is not None
        assert "intent" in result
        assert result["intent"] == UserIntent.UNKNOWN

