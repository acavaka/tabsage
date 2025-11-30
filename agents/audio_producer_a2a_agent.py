"""Audio Producer Agent for A2A - wrapper for working via A2A protocol"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from agents.audio_producer_agent import run_once as audio_producer_run_once

logger = logging.getLogger(__name__)


def create_audio_producer_a2a_agent(config: Dict[str, Any] = None) -> LlmAgent:
    """Creates Audio Producer Agent for exposure via A2A.
    
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
        name="audio_producer_a2a_agent",
        description="Audio Producer Agent exposed via A2A - produces audio from scripts using TTS",
        instruction="""You are an Audio Producer Agent for TabSage, exposed via A2A.

Your task:
1. Accept JSON request with fields: script, session_id, episode_id
2. Generate TTS prompts and audio recommendations
3. Return results in JSON format

Input JSON format:
{
  "script": {
    "segments": [...]
  },
  "session_id": "session_001",
  "episode_id": "episode_001"
}

Output JSON format:
{
  "tts_prompts": [...],
  "audio_recommendations": {...},
  "target_lufs": -16.0
}""",
    )
    
    return agent

