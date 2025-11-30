"""Scriptwriter Agent - generates podcast scripts"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from schemas.models import (
    ScriptwriterPayload, ScriptwriterResponse, ScriptSegment, Topic
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def generate_script_llm(
    topic: Topic,
    target_audience: str,
    format: str,
    model: Gemini
) -> Dict[str, Any]:
    """Generates script using LLM.
    
    Args:
        topic: Episode topic
        target_audience: Target audience
        format: Format (informative, interview, storytelling)
        model: Gemini model
        
    Returns:
        Dictionary with generation results
    """
    system_prompt = """You are a Scriptwriter for TabSage podcast. Input — topic, target audience, format. Generate episode structure: segments with timing, key facts/quotes/questions, and final script version. Specify sources/links to KG nodes.

Return JSON in format:
{
  "segments": [
    {
      "segment_type": "intro|hook|body|interview|conclusion",
      "timing": "0:00-2:30",
      "content": "segment text",
      "key_facts": ["fact 1", "fact 2"],
      "quotes": ["quote 1"],
      "questions": ["question 1"],
      "kg_references": ["node_id1", "node_id2"]
    }
  ],
  "full_script": "full script text",
  "total_estimated_minutes": 30
}"""

    try:
        topic_description = f"""Topic: {topic.title}
Why it matters: {topic.why_it_matters}
Seed nodes: {', '.join(topic.seed_nodes)}
Difficulty: {topic.difficulty}
Estimated length: {topic.estimated_length_minutes} minutes"""

        user_message = f"""topic: {topic_description}
audience: {target_audience}
format: {format}

Generate podcast script based on this topic."""

        scriptwriter_agent = LlmAgent(
            model=model,
            name="scriptwriter",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=scriptwriter_agent,
            app_name="scriptwriter",
            session_service=session_service
        )
        
        session_id = f"script_{hash(str(topic.title)) % 10000}"
        session = await session_service.create_session(
            app_name="scriptwriter",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        return {
            "status": "success",
            "segments": result.get("segments", []),
            "full_script": result.get("full_script", ""),
            "total_estimated_minutes": result.get("total_estimated_minutes", topic.estimated_length_minutes)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "segments": [],
            "full_script": "",
            "total_estimated_minutes": 0
        }
    except Exception as e:
        logger.error(f"Error in generate_script_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "segments": [],
            "full_script": "",
            "total_estimated_minutes": 0
        }


def create_scriptwriter_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Scriptwriter Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for script generation
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
        name="scriptwriter_agent",
        description="Scriptwriter Agent for TabSage - generates podcast scripts",
        instruction="""You are a Scriptwriter Agent for TabSage. Your task:

1. Accept episode topic, target audience and format
2. Generate episode structure with segments (intro, hook, body, interview, conclusion)
3. Specify timing for each segment
4. Include key facts, quotes and questions
5. Specify links to Knowledge Graph nodes
6. Create final script version

Support different formats: informative, interview, storytelling.""",
    )
    
    return agent


async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through Scriptwriter Agent.
    
    Args:
        payload: Input data (topic, target_audience, format, session_id, episode_id)
        agent: Scriptwriter Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in ScriptwriterResponse format
    """
    try:
        if "topic" in payload and isinstance(payload["topic"], dict):
            payload["topic"] = Topic(**payload["topic"])
        
        try:
            scriptwriter_payload = ScriptwriterPayload(**payload)
        except ValidationError as e:
            # If topic validation failed, try to convert
            if "topic" in payload:
                payload["topic"] = Topic(**payload["topic"]) if isinstance(payload["topic"], dict) else payload["topic"]
                scriptwriter_payload = ScriptwriterPayload(**payload)
            else:
                raise
        
        if agent is None:
            agent = create_scriptwriter_agent()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id=scriptwriter_payload.session_id
        )
        
        config = get_config()
        model = Gemini(
            model=config.get("gemini_model", GEMINI_MODEL),
            retry_options=types.HttpRetryOptions(
                attempts=3,
                exp_base=7,
                initial_delay=1,
                http_status_codes=[429, 500, 503, 504]
            )
        )
        
        generation_result = await generate_script_llm(
            scriptwriter_payload.topic,
            scriptwriter_payload.target_audience,
            scriptwriter_payload.format,
            model
        )
        
        if generation_result["status"] == "error":
            raise ValueError(generation_result.get("error_message", "Unknown error"))
        
        segments = []
        for segment_data in generation_result.get("segments", []):
            try:
                segment = ScriptSegment(**segment_data)
                segments.append(segment)
            except Exception as e:
                logger.warning(f"Failed to create ScriptSegment from data: {e}")
                continue
        
        response = ScriptwriterResponse(
            segments=segments,
            full_script=generation_result.get("full_script", ""),
            total_estimated_minutes=generation_result.get("total_estimated_minutes", 30),
            session_id=scriptwriter_payload.session_id,
            episode_id=scriptwriter_payload.episode_id
        )
        
        logger.info(f"Generated script with {len(segments)} segments for session {scriptwriter_payload.session_id}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

