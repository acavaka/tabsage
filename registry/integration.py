"""
Registry integration with Orchestrator and agents

Automatic agent discovery through registry instead of hardcoded URLs.
"""

import logging
from typing import Dict, Any, Optional

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

from observability.logging import get_logger
from registry.vertex_ai_registry import get_registry, discover_agent

logger = get_logger(__name__)


def create_remote_agent_from_registry(
    agent_name: str,
    fallback_url: Optional[str] = None
) -> Optional[RemoteA2aAgent]:
    """Creates RemoteA2aAgent using registry for discovery.
    
    Args:
        agent_name: Agent name to search in registry
        fallback_url: URL for fallback if agent not found in registry
        
    Returns:
        RemoteA2aAgent or None if not found
    """
    try:
        # Search for agent in registry
        agent_info = discover_agent(agent_name)
        
        if agent_info:
            agent_url = agent_info.get("url")
            agent_description = agent_info.get("description", f"{agent_name} agent")
            
            logger.info(f"Agent found in registry: {agent_name}", extra={
                "event_type": "agent_discovered_from_registry",
                "agent_name": agent_name,
                "agent_url": agent_url
            })
        else:
            # Fallback to hardcoded URL or provided fallback_url
            if fallback_url:
                agent_url = fallback_url
                agent_description = f"{agent_name} agent (fallback)"
                
                logger.warning(f"Agent not found in registry, using fallback: {agent_name}", extra={
                    "event_type": "agent_fallback",
                    "agent_name": agent_name,
                    "fallback_url": fallback_url
                })
            else:
                logger.error(f"Agent not found in registry and no fallback: {agent_name}")
                return None
        
        # Create RemoteA2aAgent
        remote_agent = RemoteA2aAgent(
            name=agent_name,
            description=agent_description,
            agent_card=f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}",
        )
        
        return remote_agent
    
    except Exception as e:
        logger.error(f"Error creating remote agent from registry: {e}", exc_info=True)
        return None


def get_agent_url_from_registry(
    agent_name: str,
    fallback_url: Optional[str] = None
) -> Optional[str]:
    """Gets agent URL from registry.
    
    Args:
        agent_name: Agent name
        fallback_url: URL for fallback
        
    Returns:
        Agent URL or None
    """
    agent_info = discover_agent(agent_name)
    
    if agent_info:
        return agent_info.get("url")
    
    return fallback_url

