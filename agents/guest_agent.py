"""Guest/Persona Agent - simulates guest based on KG"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from tools.kg_client import get_kg_instance
from schemas.models import GuestResponse
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def answer_as_expert_llm(
    persona_spec: str,
    question: str,
    kg_context: Optional[Dict[str, Any]] = None,
    model: Gemini = None
) -> Dict[str, Any]:
    """Answers question as expert using LLM.
    
    Args:
        persona_spec: Persona/expert specification
        question: Question to answer
        kg_context: Knowledge graph context (optional)
        model: Gemini model
        
    Returns:
        Dictionary with expert answer
    """
    if model is None:
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
    
    system_prompt = f"""You are an expert {persona_spec} (based on KG). Answer as this expert. Give short and detailed answers to questions, add links to KG sources and confidence level.

Return JSON in format:
{{
  "short_answer": "brief answer (1-2 sentences)",
  "detailed_answer": "detailed answer",
  "kg_references": ["node_id1", "node_id2"],
  "confidence": 0.0-1.0
}}"""

    kg_info = ""
    if kg_context:
        nodes_info = []
        for node in kg_context.get("nodes", [])[:20]:
            nodes_info.append({
                "node_id": node.get("node_id", ""),
                "type": node.get("type", ""),
                "canonical_name": node.get("canonical_name", "")
            })
        kg_info = f"\n\nKnowledge Graph Context:\n{json.dumps(nodes_info, ensure_ascii=False, indent=2)}"

    try:
        guest_agent = LlmAgent(
            model=model,
            name="guest_expert",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=guest_agent,
            app_name="guest",
            session_service=session_service
        )
        
        session_id = f"guest_{hash(question) % 10000}"
        session = await session_service.create_session(
            app_name="guest",
            user_id="system",
            session_id=session_id
        )
        
        user_message = f"Interview Q: {question}{kg_info}"
        
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
            "short_answer": result.get("short_answer", ""),
            "detailed_answer": result.get("detailed_answer", ""),
            "kg_references": result.get("kg_references", []),
            "confidence": result.get("confidence", 0.5)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "short_answer": "",
            "detailed_answer": "",
            "kg_references": [],
            "confidence": 0.0
        }
    except Exception as e:
        logger.error(f"Error in answer_as_expert_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "short_answer": "",
            "detailed_answer": "",
            "kg_references": [],
            "confidence": 0.0
        }


def create_guest_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Guest/Persona Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for guest simulation
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    def get_kg_context(limit: int = 20) -> Dict[str, Any]:
        """Gets context from knowledge graph.
        
        Args:
            limit: Maximum number of nodes
            
        Returns:
            Dictionary with graph context
        """
        kg = get_kg_instance()
        return kg.get_snapshot(limit=limit)
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="guest_agent",
        description="Guest/Persona Agent for TabSage - simulates expert based on KG",
        instruction="""You are a Guest/Persona Agent for TabSage. Your task:

1. Accept persona/expert specification
2. Answer questions as this expert
3. Use context from Knowledge Graph via get_kg_context
4. Provide short and detailed answers
5. Reference KG nodes and confidence level

Use get_kg_context to get relevant information from the knowledge graph.""",
        tools=[get_kg_context],
    )
    
    return agent


# Note: guest_agent has different signature, add observability manually
async def run_once(
    persona_spec: str,
    question: str,
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes question through Guest/Persona Agent.
    
    Args:
        persona_spec: Persona specification (e.g., "oncologist", "AI researcher")
        question: Question to answer
        agent: Guest Agent (if None, creates new one)
        
    Returns:
        Dictionary with answer in GuestResponse format
    """
    from observability.tracing import trace_span
    import time
    
    start_time = time.time()
    session_id = f"guest_{hash(question) % 10000}"
    
    logger.agent_start("guest_agent", session_id, {"persona": persona_spec, "question": question[:50]})
    
    try:
        with trace_span("agent.guest_agent", {"agent.name": "guest_agent", "session.id": session_id}):
            kg = get_kg_instance()
            kg_context = kg.get_snapshot(limit=20)
            
            if agent is None:
                agent = create_guest_agent()
            
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
            
            answer_result = await answer_as_expert_llm(
                persona_spec,
                question,
                kg_context,
                model
            )
            
            if answer_result["status"] == "error":
                raise ValueError(answer_result.get("error_message", "Unknown error"))
            
            response = GuestResponse(
                short_answer=answer_result.get("short_answer", ""),
                detailed_answer=answer_result.get("detailed_answer", ""),
                kg_references=answer_result.get("kg_references", []),
                confidence=answer_result.get("confidence", 0.5)
            )
            
            logger.info(f"Guest answered question as {persona_spec}")
            
            duration_ms = (time.time() - start_time) * 1000
            logger.agent_complete("guest_agent", session_id, duration_ms)
            
            return response.dict()
            
    except Exception as e:
        logger.agent_error("guest_agent", session_id, str(e))
        return {
            "status": "error",
            "error_message": str(e)
        }

