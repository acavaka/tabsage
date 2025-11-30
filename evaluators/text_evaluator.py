"""Text evaluator - evaluates text/script quality"""

import json
import logging
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config

logger = logging.getLogger(__name__)


async def evaluate_text_llm(text: str, model: Gemini) -> Dict[str, Any]:
    """Evaluates text using LLM.
    
    Args:
        text: Text to evaluate
        model: Gemini model
        
    Returns:
        Dictionary with evaluations
    """
    system_prompt = """You are an Evaluator. Evaluate text/script on: factuality (0-1), coherence (0-1), relevance (0-1), hallucination_notes (text). Provide brief explanations.

Return JSON in format:
{
  "factuality": 0.0-1.0,
  "coherence": 0.0-1.0,
  "relevance": 0.0-1.0,
  "hallucination_notes": "notes on hallucinations",
  "explanation": "brief explanation of evaluations"
}"""

    try:
        evaluator_agent = LlmAgent(
            model=model,
            name="text_evaluator",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=evaluator_agent,
            app_name="evaluator",
            session_service=session_service
        )
        
        session_id = f"eval_{hash(text) % 10000}"
        session = await session_service.create_session(
            app_name="evaluator",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=text)]
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
            "factuality": result.get("factuality", 0.5),
            "coherence": result.get("coherence", 0.5),
            "relevance": result.get("relevance", 0.5),
            "hallucination_notes": result.get("hallucination_notes", ""),
            "explanation": result.get("explanation", "")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "factuality": 0.0,
            "coherence": 0.0,
            "relevance": 0.0,
            "hallucination_notes": "",
            "explanation": ""
        }
    except Exception as e:
        logger.error(f"Error in evaluate_text_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "factuality": 0.0,
            "coherence": 0.0,
            "relevance": 0.0,
            "hallucination_notes": "",
            "explanation": ""
        }

