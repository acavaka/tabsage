"""Evaluator Agent for A2A - wrapper for working via A2A protocol"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from agents.evaluator_agent import run_once as evaluator_run_once

logger = logging.getLogger(__name__)


def create_evaluator_a2a_agent(config: Dict[str, Any] = None) -> LlmAgent:
    """Creates Evaluator Agent for exposure via A2A.
    
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
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="evaluator_a2a_agent",
        description="Evaluator Agent exposed via A2A - evaluates text and audio quality",
        instruction="""You are an Evaluator Agent for TabSage, exposed via A2A.

Your task:
1. Accept JSON request with fields: content_type, content, session_id, episode_id
2. Evaluate content quality (text or audio)
3. Return results in JSON format

Input JSON format:
{
  "content_type": "text|audio",
  "content": {...},
  "session_id": "session_001",
  "episode_id": "episode_001"
}

Output JSON format:
{
  "text_evaluation": {...},
  "audio_evaluation": {...}
}""",
    )
    
    return agent

