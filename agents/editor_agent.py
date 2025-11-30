"""Editor Agent - human-in-the-loop review and edits"""

import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import ToolContext, FunctionTool
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from schemas.models import (
    EditorPayload, EditorResponse, EditorReview, ScriptwriterResponse
)
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


def request_script_review(
    script_summary: str,
    script_segments_count: int,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Requests script review from human.
    
    Args:
        script_summary: Brief script description
        script_segments_count: Number of segments
        tool_context: ToolContext for human-in-loop
        
    Returns:
        Dictionary with results
    """
    # If this is first call - request confirmation
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=f"Script Review Required\n\n"
                 f"Script Summary: {script_summary}\n"
                 f"Segments: {script_segments_count}\n\n"
                 f"Do you approve this script for publication?",
            payload={
                "script_summary": script_summary,
                "segments_count": script_segments_count
            }
        )
        return {
            "status": "pending",
            "message": "Waiting for human review..."
        }
    
    # If received confirmation
    if tool_context.tool_confirmation.confirmed:
        return {
            "status": "approved",
            "message": "Script approved by human reviewer"
        }
    else:
        return {
            "status": "rejected",
            "message": "Script rejected by human reviewer",
            "feedback": tool_context.tool_confirmation.payload.get("feedback", "")
        }


def apply_script_edits(
    script: Dict[str, Any],
    edits: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Applies edits to script.
    
    Args:
        script: Original script
        edits: Edit text
        tool_context: ToolContext
        
    Returns:
        Dictionary with updated script
    """
    # In production there will be LLM for applying edits
    logger.info(f"Applying edits to script: {edits[:100]}...")
    
    return {
        "status": "success",
        "message": "Edits applied (mock - actual editing not implemented)",
        "revised_script": script  # In production this will be actually edited script
    }


def create_editor_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Editor Agent with human-in-loop.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for review
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
        name="editor_agent",
        description="Editor Agent for TabSage - human-in-loop review and edits",
        instruction="""You are an Editor Agent for TabSage. Your task:

1. Accept ready script for review
2. Use request_script_review to request human review
3. If script rejected, use apply_script_edits to apply edits
4. Return final review result

Always request human confirmation before publishing.""",
        tools=[
            FunctionTool(func=request_script_review),
            FunctionTool(func=apply_script_edits)
        ],
    )
    
    return agent


@observe_agent("editor_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None,
    auto_approve: bool = False
) -> Dict[str, Any]:
    """Processes one payload through Editor Agent.
    
    Args:
        payload: Input data (script, session_id, episode_id)
        agent: Editor Agent (if None, creates new one)
        auto_approve: Auto-approve (for tests, default False)
        
    Returns:
        Dictionary with processing results in EditorResponse format
    """
    try:
        if "script" in payload and isinstance(payload["script"], dict):
            payload["script"] = ScriptwriterResponse(**payload["script"])
        
        editor_payload = EditorPayload(**payload)
        
        if agent is None:
            agent = create_editor_agent()
        
        script = editor_payload.script
        
        if auto_approve:
            review = EditorReview(
                approved=True,
                feedback="Auto-approved for testing"
            )
        else:
            review = EditorReview(
                approved=True,
                feedback="Mock approval - implement real human review workflow"
            )
        
        response = EditorResponse(
            approved=review.approved,
            review=review,
            revised_script=None,  # In production, edited script will be here if edits needed
            session_id=editor_payload.session_id,
            episode_id=editor_payload.episode_id
        )
        
        logger.info(f"Editor review complete for session {editor_payload.session_id}: {'approved' if review.approved else 'rejected'}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

