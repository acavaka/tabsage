"""Ingest Agent with A2A integration for calling KG Builder"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config, KG_BUILDER_A2A_URL
from agents.ingest_agent import run_once as ingest_run_once_base
from schemas.models import IngestResponse

logger = logging.getLogger(__name__)


async def run_once_with_a2a(
    payload: Dict[str, Any],
    kg_builder_url: Optional[str] = None
) -> Dict[str, Any]:
    """Processes payload via Ingest Agent and sends to KG Builder via A2A.
    
    Args:
        payload: Input data (raw_text, metadata, session_id, episode_id)
        kg_builder_url: KG Builder Agent URL for A2A (if None, uses from config)
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Step 1: Process via Ingest Agent
        ingest_result = await ingest_run_once_base(payload)
        
        if "error_message" in ingest_result:
            return ingest_result
        
        # Step 2: Send to KG Builder via A2A
        if kg_builder_url is None:
            kg_builder_url = KG_BUILDER_A2A_URL
        
        if kg_builder_url:
            logger.info(f"Sending to KG Builder via A2A: {kg_builder_url}")
            
            try:
                remote_kg_builder = RemoteA2aAgent(
                    name="kg_builder_agent",
                    description="KG Builder Agent for extracting entities and relations",
                    agent_card=f"{kg_builder_url}{AGENT_CARD_WELL_KNOWN_PATH}",
                )
                
                kg_payload = {
                    "chunks": ingest_result.get("chunks", []),
                    "title": ingest_result.get("title", ""),
                    "language": ingest_result.get("language", ""),
                    "session_id": ingest_result.get("session_id"),
                    "episode_id": ingest_result.get("episode_id"),
                    "metadata": payload.get("metadata", {})
                }
                
                config = get_config()
                retry_config = types.HttpRetryOptions(
                    attempts=5,
                    exp_base=7,
                    initial_delay=1,
                    http_status_codes=[429, 500, 503, 504]
                )
                
                orchestrator_agent = LlmAgent(
                    model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
                    name="ingest_orchestrator",
                    description="Orchestrates Ingest and KG Builder agents",
                    instruction="""You are an orchestrator for Ingest and KG Builder agents.

Your task:
1. Accept results from Ingest Agent (chunks, title, language)
2. Send them to KG Builder Agent via sub-agent kg_builder_agent
3. Return results

Use kg_builder_agent to process chunks.""",
                    sub_agents=[remote_kg_builder],
                )
                
                session_service = InMemorySessionService()
                runner = Runner(
                    agent=orchestrator_agent,
                    app_name="tabsage",
                    session_service=session_service
                )
                
                session = await session_service.create_session(
                    app_name="tabsage",
                    user_id="system",
                    session_id=ingest_result.get("session_id", "a2a_session")
                )
                
                user_message = f"""Process the following chunks via kg_builder_agent:

Chunks: {len(kg_payload['chunks'])} pieces
Title: {kg_payload['title']}
Language: {kg_payload['language']}

Use kg_builder_agent to extract entities and relationships from these chunks.
Return extraction results."""
                
                response_text = ""
                async for event in runner.run_async(
                    user_id="system",
                    session_id=session.id,
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part(text=user_message)]
                    )
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                response_text += part.text
                
                logger.info(f"KG Builder response received via A2A")
                
                ingest_result["kg_builder_called"] = True
                ingest_result["kg_builder_url"] = kg_builder_url
                
            except Exception as e:
                logger.warning(f"Failed to call KG Builder via A2A: {e}")
                ingest_result["kg_builder_called"] = False
                ingest_result["kg_builder_error"] = str(e)
        
        return ingest_result
        
    except Exception as e:
        logger.error(f"Error in run_once_with_a2a: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

