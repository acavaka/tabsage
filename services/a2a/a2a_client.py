"""A2A Client utilities for calling agents via RemoteA2aAgent"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from registry.integration import get_agent_url_from_registry

logger = logging.getLogger(__name__)


async def call_agent_via_a2a(
    agent_url: str,
    agent_name: str,
    agent_description: str,
    payload: Dict[str, Any],
    session_id: str,
    user_message_template: Optional[str] = None,
    use_registry: bool = True
) -> Dict[str, Any]:
    """Calls agent via A2A protocol.
    
    Args:
        agent_url: Agent URL (will be used as fallback if use_registry=True)
        agent_name: Agent name for RemoteA2aAgent
        agent_description: Agent description
        payload: Payload to send to agent
        session_id: Session ID
        user_message_template: Message template (if None, JSON payload is used)
        use_registry: Use registry to get URL (default: True)
        
    Returns:
        Dictionary with call results
    """
    try:
        if use_registry and agent_name:
            registry_url = get_agent_url_from_registry(agent_name, fallback_url=agent_url)
            if registry_url:
                agent_url = registry_url
        remote_agent = RemoteA2aAgent(
            name=agent_name,
            description=agent_description,
            agent_card=f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}",
        )
        
        config = get_config()
        retry_config = types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504]
        )
        
        orchestrator_agent = LlmAgent(
            model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
            name=f"{agent_name}_orchestrator",
            description=f"Orchestrates calls to {agent_name}",
            instruction=f"""You are an orchestrator for calling {agent_name}.

Your task:
1. Accept data from user
2. Send it to {agent_name} via sub-agent {agent_name}
3. Return results

Use {agent_name} to process the request.""",
            sub_agents=[remote_agent],
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
            session_id=session_id
        )
        
        if user_message_template:
            user_message = user_message_template.format(**payload)
        else:
            # By default send JSON
            user_message = f"""Process the following data via {agent_name}:

{json.dumps(payload, ensure_ascii=False, indent=2)}

Use {agent_name} to process. Return results."""
        
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
        
        logger.info(f"Response received from {agent_name} via A2A")
        
        try:
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end != -1:
                    response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end != -1:
                    response_text = response_text[json_start:json_end].strip()
            
            result = json.loads(response_text)
            return {
                "status": "success",
                "result": result
            }
        except json.JSONDecodeError:
            # If failed to parse JSON, return text
            return {
                "status": "success",
                "result": {"response": response_text}
            }
        
    except Exception as e:
        logger.error(f"Error calling {agent_name} via A2A: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e)
        }

