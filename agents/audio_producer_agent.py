"""Audio Producer Agent - creates audio from text (TTS + processing)"""

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
    AudioProducerPayload, AudioProducerResponse, TTSPrompt, AudioRecommendation, ScriptSegment
)
from tools.tts import synthesize_speech, batch_synthesize
from tools.audio_utils import normalize_audio, mix_audio
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def generate_audio_production_llm(
    segments: list,
    full_script: str,
    model: Gemini
) -> Dict[str, Any]:
    """Generates audio production recommendations using LLM.
    
    Args:
        segments: List of script segments
        full_script: Full script text
        model: Gemini model
        
    Returns:
        Dictionary with recommendations
    """
    system_prompt = """You are an Audio Producer. Input — segmented script with timing and tone markers. Output: 1) SSML / TTS prompts for each segment; 2) music and effects recommendations; 3) target loudness (LUFS) and post-processing steps.

Return JSON in format:
{
  "tts_prompts": [
    {
      "segment_id": "segment_1",
      "ssml": "<speak>...</speak>",
      "text": "text for synthesis",
      "voice": "default|male|female",
      "speed": 1.0,
      "tone": "neutral|excited|calm"
    }
  ],
  "recommendations": {
    "music_track": "track name",
    "sound_effects": ["effect1", "effect2"],
    "target_lufs": -16.0,
    "post_processing": ["normalize", "compress"]
  }
}"""

    segments_info = []
    for seg in segments:
        segments_info.append({
            "segment_type": seg.get("segment_type", ""),
            "timing": seg.get("timing", ""),
            "content": seg.get("content", "")[:200]  # First 200 characters
        })
    
    script_info = f"""Segments: {json.dumps(segments_info, ensure_ascii=False, indent=2)}
Full script length: {len(full_script)} characters"""

    try:
        producer_agent = LlmAgent(
            model=model,
            name="audio_producer",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=producer_agent,
            app_name="audio_producer",
            session_service=session_service
        )
        
        session_id = f"audio_{hash(full_script) % 10000}"
        session = await session_service.create_session(
            app_name="audio_producer",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=script_info)]
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
            "tts_prompts": result.get("tts_prompts", []),
            "recommendations": result.get("recommendations", {})
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "tts_prompts": [],
            "recommendations": {}
        }
    except Exception as e:
        logger.error(f"Error in generate_audio_production_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "tts_prompts": [],
            "recommendations": {}
        }


def create_audio_producer_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Audio Producer Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for audio production
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
        name="audio_producer_agent",
        description="Audio Producer Agent for TabSage - creates audio from text",
        instruction="""You are an Audio Producer Agent for TabSage. Your task:

1. Accept segmented script
2. Generate TTS prompts for each segment
3. Suggest music and sound effects recommendations
4. Specify target loudness (LUFS) and post-processing steps
5. Return structured data for audio production""",
    )
    
    return agent


@observe_agent("audio_producer_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through Audio Producer Agent.
    
    Args:
        payload: Input data (segments, full_script, session_id, episode_id)
        agent: Audio Producer Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in AudioProducerResponse format
    """
    try:
        if "segments" in payload:
            segments_data = payload["segments"]
            if segments_data and isinstance(segments_data[0], dict):
                from schemas.models import ScriptSegment
                payload["segments"] = [ScriptSegment(**s) for s in segments_data]
        
        audio_payload = AudioProducerPayload(**payload)
        
        if agent is None:
            agent = create_audio_producer_agent()
        
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
        
        segments_dict = [s.dict() if hasattr(s, 'dict') else s for s in audio_payload.segments]
        
        production_result = await generate_audio_production_llm(
            segments_dict,
            audio_payload.full_script,
            model
        )
        
        if production_result["status"] == "error":
            raise ValueError(production_result.get("error_message", "Unknown error"))
        
        tts_prompts = []
        for prompt_data in production_result.get("tts_prompts", []):
            try:
                prompt = TTSPrompt(**prompt_data)
                tts_prompts.append(prompt)
            except Exception as e:
                logger.warning(f"Failed to create TTSPrompt from data: {e}")
                continue
        
        rec_data = production_result.get("recommendations", {})
        recommendations = AudioRecommendation(
            music_track=rec_data.get("music_track"),
            sound_effects=rec_data.get("sound_effects", []),
            target_lufs=rec_data.get("target_lufs", -16.0),
            post_processing=rec_data.get("post_processing", [])
        )
        
        response = AudioProducerResponse(
            tts_prompts=tts_prompts,
            recommendations=recommendations,
            session_id=audio_payload.session_id,
            episode_id=audio_payload.episode_id
        )
        
        logger.info(f"Generated audio production plan with {len(tts_prompts)} TTS prompts")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

