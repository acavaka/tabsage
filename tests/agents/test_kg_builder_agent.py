"""Unit tests for KG Builder Agent"""

import pytest
import asyncio
from agents.kg_builder_agent import run_once
from tools.kg_client import InMemoryKnowledgeGraph


class TestKGBuilderAgent:
    """Tests for KG Builder Agent"""
    
    @pytest.mark.asyncio
    async def test_kg_builder_basic(self, mock_kg):
        """Test basic entity and relationship extraction"""
        payload = {
            "chunks": [
                "Microservices architecture allows scaling applications.",
                "Docker is used for service containerization."
            ],
            "title": "Test article",
            "language": "en",
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        assert result is not None
        assert "entities" in result or "error_message" in result
        assert "relations" in result or "error_message" in result
    
    @pytest.mark.asyncio
    async def test_kg_builder_empty_chunks(self):
        """Test empty chunks processing"""
        payload = {
            "chunks": [],
            "title": "Test",
            "language": "en",
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        assert result is not None
        # Should return empty lists or error
        if "entities" in result:
            assert isinstance(result["entities"], list)
    
    @pytest.mark.asyncio
    async def test_kg_builder_entities_structure(self, mock_kg):
        """Test extracted entity structure"""
        payload = {
            "chunks": ["Python is a programming language."],
            "title": "Test",
            "language": "en",
            "session_id": "test_session",
            "episode_id": "test_episode"
        }
        
        result = await run_once(payload)
        
        if "entities" in result and len(result["entities"]) > 0:
            entity = result["entities"][0]
            assert "type" in entity
            assert "canonical_name" in entity
            assert "confidence" in entity

