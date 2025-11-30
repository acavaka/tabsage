"""Topic Discovery Agent for A2A - wrapper for working via A2A protocol"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.agents.function_tool import FunctionTool
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from agents.topic_discovery_agent import run_once as topic_discovery_run_once

logger = logging.getLogger(__name__)


async def process_topic_discovery(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Processes Topic Discovery request via run_once."""
    try:
        result = await topic_discovery_run_once(payload)
        return result
    except Exception as e:
        logger.error(f"Error in process_topic_discovery: {e}")
        return {"error_message": str(e)}


def create_topic_discovery_a2a_agent(config: Dict[str, Any] = None) -> LlmAgent:
    """Creates Topic Discovery Agent for exposure via A2A.
    
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
    
    topic_discovery_tool = FunctionTool(
        name="discover_topics",
        description="Discovers podcast topics from knowledge graph. Takes JSON payload with session_id, episode_id, max_topics.",
        func=process_topic_discovery
    )
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="topic_discovery_a2a_agent",
        description="Topic Discovery Agent exposed via A2A - discovers podcast topics from knowledge graph",
        instruction="""You are a Topic Discovery Agent for TabSage, exposed via A2A.

Your task:
1. Accept JSON request with fields: session_id, episode_id, max_topics (optional)
2. Use discover_topics tool to process request
3. Return results

Use discover_topics tool for all requests.""",
        tools=[topic_discovery_tool],
    )
    
    return agent

