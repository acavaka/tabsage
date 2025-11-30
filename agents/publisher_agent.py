"""Publisher Agent - publishes podcasts to hosting and social media"""

import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from schemas.models import (
    PublisherPayload, PublisherResponse, PublicationMetadata, ScriptwriterResponse
)
from tools.publisher import publish_to_hosting, publish_to_social_media
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


def create_publisher_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Publisher Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for publishing
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
        name="publisher_agent",
        description="Publisher Agent for TabSage - publishes podcasts",
        instruction="""You are a Publisher Agent for TabSage. Your task:

1. Accept ready script and audio file
2. Prepare publication metadata (title, description, tags, transcript)
3. Publish to podcast hosting
4. Publish information to social media
5. Return publication URLs""",
        tools=[publish_to_hosting, publish_to_social_media],
    )
    
    return agent


@observe_agent("publisher_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through Publisher Agent.
    
    Args:
        payload: Input data (script, audio_file_path, session_id, episode_id)
        agent: Publisher Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in PublisherResponse format
    """
    try:
        # Convert script from dict to ScriptwriterResponse if needed
        if "script" in payload and isinstance(payload["script"], dict):
            from schemas.models import ScriptwriterResponse
            payload["script"] = ScriptwriterResponse(**payload["script"])
        
        # Validate payload
        publisher_payload = PublisherPayload(**payload)
        
        script = publisher_payload.script
        
        title = f"Episode {publisher_payload.episode_id or 'Unknown'}"
        if script.segments:
            first_segment = script.segments[0]
            if first_segment.segment_type == "intro":
                title = first_segment.content[:100] + "..." if len(first_segment.content) > 100 else first_segment.content
        
        metadata = PublicationMetadata(
            title=title,
            description=script.full_script[:500] + "..." if len(script.full_script) > 500 else script.full_script,
            tags=["AI", "podcast", "knowledge graph"],
            transcript=script.full_script,
            duration_minutes=script.total_estimated_minutes
        )
        
        # Publish to hosting
        publication_urls = {}
        
        if publisher_payload.audio_file_path:
            hosting_result = publish_to_hosting(
                publisher_payload.audio_file_path,
                metadata.dict(),
                platform="libsyn"
            )
            if hosting_result["status"] == "success":
                publication_urls["hosting"] = hosting_result["publication_url"]
        else:
            logger.warning("No audio file provided, skipping hosting publication")
        
        # Publish to social media
        social_result = publish_to_social_media(
            metadata.dict(),
            platforms=["twitter", "linkedin"]
        )
        if social_result["status"] == "success":
            publication_urls.update(social_result.get("urls", {}))
        
        response = PublisherResponse(
            published=len(publication_urls) > 0,
            publication_urls=publication_urls,
            metadata=metadata,
            session_id=publisher_payload.session_id,
            episode_id=publisher_payload.episode_id
        )
        
        logger.info(f"Published episode {publisher_payload.episode_id} to {len(publication_urls)} platforms")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

