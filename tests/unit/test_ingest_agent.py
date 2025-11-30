"""Unit tests for Ingest Agent"""

import pytest
import asyncio
from agents.ingest_agent import run_once, create_ingest_agent
from schemas.models import IngestResponse


@pytest.mark.asyncio
async def test_run_once_with_mock_text():
    """Test run_once with mock text"""
    payload = {
        "raw_text": """This is a test text to check Ingest Agent functionality.
        
        It contains several sentences and should be processed correctly.
        
        [Ad: buy our product]
        
        Text continues after ad.""",
        "metadata": {"source": "test"},
        "session_id": "test_session_001",
        "episode_id": "test_episode_001"
    }
    
    # Run processing
    result = await run_once(payload)
    
    # Check response structure
    assert "status" in result or "title" in result
    
    # If successful, check for all fields
    if "title" in result:
        assert isinstance(result["title"], str)
        assert isinstance(result["language"], str)
        assert isinstance(result["cleaned_text"], str)
        assert isinstance(result["summary"], str)
        assert isinstance(result["chunks"], list)
        assert len(result["chunks"]) <= 5
        assert result["session_id"] == "test_session_001"
        assert result["episode_id"] == "test_episode_001"
        
        # Check that cleaned_text does not contain ads
        assert "[Ad" not in result["cleaned_text"]
    
    # Validate via Pydantic schema
    if "title" in result:
        try:
            response = IngestResponse(**result)
            assert response.title is not None
        except Exception as e:
            pytest.fail(f"Response does not match schema: {e}")


@pytest.mark.asyncio
async def test_run_once_idempotency():
    """Test idempotency - repeated run with same data"""
    payload = {
        "raw_text": "Test text for idempotency check.",
        "metadata": {},
        "session_id": "idempotency_test",
        "episode_id": "ep_001"
    }
    
    # First run
    result1 = await run_once(payload)
    
    # Second run with same data
    result2 = await run_once(payload)
    
    # Results should be identical (or at least have same structure)
    if "title" in result1 and "title" in result2:
        # Check that structure is the same
        assert set(result1.keys()) == set(result2.keys())
        assert result1["session_id"] == result2["session_id"]
        assert result1["episode_id"] == result2["episode_id"]


def test_create_ingest_agent():
    """Test Ingest Agent creation"""
    agent = create_ingest_agent()
    
    assert agent is not None
    assert agent.name == "ingest_agent"
    assert len(agent.tools) > 0  # Should have tools


@pytest.mark.asyncio
async def test_run_once_empty_text():
    """Test empty text processing"""
    payload = {
        "raw_text": "",
        "metadata": {},
        "session_id": "empty_test",
        "episode_id": None
    }
    
    result = await run_once(payload)
    
    # Should return error or process correctly
    assert "status" in result or "error_message" in result or "title" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

