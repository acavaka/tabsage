"""Evaluator Agent - evaluates text and audio quality"""

import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from schemas.models import (
    EvaluatorPayload, EvaluatorResponse, TextEvaluation, AudioEvaluation
)
from evaluators.text_evaluator import evaluate_text_llm
from evaluators.audio_evaluator import evaluate_audio
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


def create_evaluator_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Evaluator Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for evaluation
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
        name="evaluator_agent",
        description="Evaluator Agent for TabSage - evaluates text and audio quality",
        instruction="""You are an Evaluator Agent for TabSage. Your task:

1. Evaluate text/script by metrics: factuality, coherence, relevance
2. Detect hallucinations
3. Evaluate audio by metrics: SNR, LUFS, clipping, perceived quality
4. Provide improvement recommendations""",
        tools=[evaluate_audio],  # Text evaluation via LLM directly
    )
    
    return agent


@observe_agent("evaluator_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through Evaluator Agent.
    
    Args:
        payload: Input data (text, audio_file_path, audio_metrics, session_id, episode_id)
        agent: Evaluator Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in EvaluatorResponse format
    """
    try:
        evaluator_payload = EvaluatorPayload(**payload)
        
        text_evaluation = None
        audio_evaluation = None
        
        # Text evaluation
        if evaluator_payload.text:
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
            
            text_result = await evaluate_text_llm(evaluator_payload.text, model)
            
            if text_result["status"] == "success":
                text_evaluation = TextEvaluation(
                    factuality=text_result.get("factuality", 0.5),
                    coherence=text_result.get("coherence", 0.5),
                    relevance=text_result.get("relevance", 0.5),
                    hallucination_notes=text_result.get("hallucination_notes", ""),
                    explanation=text_result.get("explanation", "")
                )
        
        # Audio evaluation
        if evaluator_payload.audio_file_path or evaluator_payload.audio_metrics:
            audio_result = evaluate_audio(
                evaluator_payload.audio_file_path,
                evaluator_payload.audio_metrics
            )
            
            if audio_result["status"] == "success":
                audio_evaluation = AudioEvaluation(
                    snr=audio_result.get("snr", 20.0),
                    lufs=audio_result.get("lufs", -16.0),
                    clipping=audio_result.get("clipping", False),
                    perceived_quality=audio_result.get("perceived_quality", 3),
                    suggestions=audio_result.get("suggestions", "")
                )
        
        response = EvaluatorResponse(
            text_evaluation=text_evaluation,
            audio_evaluation=audio_evaluation,
            session_id=evaluator_payload.session_id,
            episode_id=evaluator_payload.episode_id
        )
        
        logger.info(f"Evaluation complete for session {evaluator_payload.session_id}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

