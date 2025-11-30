"""KG Builder Agent for A2A - wrapper for working via A2A protocol"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from agents.kg_builder_agent import run_once as kg_builder_run_once

logger = logging.getLogger(__name__)


def create_kg_builder_a2a_agent(config: Dict[str, Any] = None) -> LlmAgent:
    """Creates KG Builder Agent for exposure via A2A.
    
    This agent accepts text requests in JSON format and calls run_once.
    
    Args:
        config: Configuration (optional)
        
    Returns:
        LlmAgent configured for A2A
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    async def process_kg_builder_request(request_text: str) -> Dict[str, Any]:
        """Processes KG Builder request via run_once.
        
        Args:
            request_text: JSON string with payload for KG Builder
            
        Returns:
            Dictionary with results
        """
        try:
            payload = json.loads(request_text)
            result = await kg_builder_run_once(payload)
            
            return {
                "status": "success",
                "result": result
            }
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error_message": f"Invalid JSON: {e}"
            }
        except Exception as e:
            logger.error(f"Error in process_kg_builder_request: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="kg_builder_a2a_agent",
        description="KG Builder Agent exposed via A2A - extracts entities and relations, updates knowledge graph",
        instruction="""You are a KG Builder Agent for TabSage, exposed via A2A.

Your task:
1. Accept JSON request with fields: chunks, title, language, session_id, episode_id
2. Extract entities and relationships from chunks
3. Update knowledge graph
4. Return results in JSON format

Input JSON format:
{
  "chunks": ["chunk text 1", "chunk text 2"],
  "title": "title",
  "language": "ru",
  "session_id": "session_001",
  "episode_id": "episode_001"
}

Output JSON format:
{
  "entities": [...],
  "relations": [...],
  "chunk_extractions": [...],
  "graph_updated": true
}""",
    )
    
    return agent

