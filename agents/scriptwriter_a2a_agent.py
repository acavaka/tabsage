"""Scriptwriter Agent for A2A - wrapper for working via A2A protocol"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.agents.function_tool import FunctionTool
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from agents.scriptwriter_agent import run_once as scriptwriter_run_once

logger = logging.getLogger(__name__)


async def process_scriptwriter(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Processes Scriptwriter request via run_once."""
    try:
        result = await scriptwriter_run_once(payload)
        return result
    except Exception as e:
        logger.error(f"Error in process_scriptwriter: {e}")
        return {"error_message": str(e)}


def create_scriptwriter_a2a_agent(config: Dict[str, Any] = None) -> LlmAgent:
    """Creates Scriptwriter Agent for exposure via A2A.
    
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
    
    scriptwriter_tool = FunctionTool(
        name="generate_script",
        description="Generates podcast script from topic. Takes JSON payload with topic, session_id, episode_id, format.",
        func=process_scriptwriter
    )
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="scriptwriter_a2a_agent",
        description="Scriptwriter Agent exposed via A2A - generates podcast scripts from topics",
        instruction="""You are a Scriptwriter Agent for TabSage, exposed via A2A.

Your task:
1. Accept JSON request with fields: topic, session_id, episode_id, format (optional)
2. Use generate_script tool to process request
3. Return results

Use generate_script tool for all requests.""",
        tools=[scriptwriter_tool],
    )
    
    return agent

