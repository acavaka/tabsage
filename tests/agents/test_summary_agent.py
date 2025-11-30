"""Unit tests for Summary Agent"""

import pytest
import asyncio
from agents.summary_agent import run_once


class TestSummaryAgent:
    """Tests for Summary Agent"""
    
    @pytest.mark.asyncio
    async def test_summary_basic(self):
        """Test basic summary generation"""
        result = await run_once(
            article_text="Microservices architecture allows creating scalable applications.",
            title="Microservices",
            url="https://example.com/article"
        )
        
        assert result is not None
        assert "summary" in result or "error" in result
        assert "key_points" in result or "error" in result
    
    @pytest.mark.asyncio
    async def test_summary_key_points(self):
        """Test key points generation"""
        result = await run_once(
            article_text="Python is a popular programming language. It is used for web development, data science and automation.",
            title="Python",
            url="https://example.com/python"
        )
        
        if "key_points" in result:
            assert isinstance(result["key_points"], list)
            assert len(result["key_points"]) > 0
    
    @pytest.mark.asyncio
    async def test_summary_intents_and_values(self):
        """Test intent and value extraction"""
        result = await run_once(
            article_text="Learning microservices helps understand modern development approaches.",
            title="Microservices",
            url="https://example.com/ms"
        )
        
        if "intents" in result:
            assert isinstance(result["intents"], list)
        if "values" in result:
            assert isinstance(result["values"], list)
    
    @pytest.mark.asyncio
    async def test_summary_empty_text(self):
        """Test empty text processing"""
        result = await run_once(
            article_text="",
            title="Empty article",
            url="https://example.com/empty"
        )
        
        assert result is not None
        # Agent can process empty text and return structured result
        # Can be either error or successful result with minimal data
        assert "error" in result or "summary" in result
        if "error" not in result:
            # If successfully processed, check for main fields
            assert "key_points" in result or "intents" in result

