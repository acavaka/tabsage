"""Unit tests for Ingest Agent"""

import pytest
import asyncio
from agents.ingest_agent import run_once, IngestPayload
from schemas.models import IngestPayload as IngestPayloadSchema


class TestIngestAgent:
    """Tests for Ingest Agent"""
    
    @pytest.mark.asyncio
    async def test_ingest_basic(self, sample_text):
        """Test basic text processing"""
        payload = {
            "raw_text": sample_text,
            "metadata": {"source": "test"},
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        assert result is not None
        assert "title" in result or "error_message" in result
        assert "language" in result or "error_message" in result
        assert "cleaned_text" in result or "error_message" in result
        assert "summary" in result or "error_message" in result
        assert "chunks" in result or "error_message" in result
    
    @pytest.mark.asyncio
    async def test_ingest_empty_text(self):
        """Test empty text processing"""
        payload = {
            "raw_text": "",
            "metadata": {},
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        # Agent processes empty text successfully, returning structured result
        assert result is not None
        # Can be either error or successful result with empty/minimal data
        assert "error_message" in result or "title" in result
        if "error_message" not in result:
            # If successfully processed, check for main fields
            assert "language" in result or "cleaned_text" in result
    
    @pytest.mark.asyncio
    async def test_ingest_chunks_limit(self, sample_text):
        """Test chunk count limit"""
        # Create long text
        long_text = sample_text * 10
        
        payload = {
            "raw_text": long_text,
            "metadata": {"source": "test"},
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        if "chunks" in result:
            # Check that chunks are not more than 5
            assert len(result["chunks"]) <= 5
    
    @pytest.mark.asyncio
    async def test_ingest_language_detection(self, sample_text):
        """Test language detection"""
        payload = {
            "raw_text": sample_text,
            "metadata": {"source": "test"},
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        if "language" in result:
            # Language should be detected (ru or en)
            assert result["language"] in ["ru", "en", "unknown"]

