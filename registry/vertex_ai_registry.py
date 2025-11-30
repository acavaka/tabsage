"""
Vertex AI Agent Builder Registry - centralized registry for A2A agents

Based on Day 5a: Agent2Agent Communication and Day 5b: Deployment
Uses Vertex AI Agent Builder for centralized agent management.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import vertexai
    from vertexai import agent_engines
    from google.cloud import aiplatform
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

from observability.logging import get_logger
from core.config import GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION

logger = get_logger(__name__)


class VertexAIAgentRegistry:
    """
    Centralized registry for A2A agents via Vertex AI Agent Builder.
    
    Functions:
    - Agent registration on deployment
    - Automatic agent discovery
    - Version management
    - Agent metadata (URL, capabilities, version)
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None
    ):
        """Initialize Vertex AI Agent Registry.
        
        Args:
            project_id: GCP project ID (if None, uses from config)
            location: Vertex AI location (if None, uses from config)
        """
        if not HAS_VERTEX_AI:
            raise ImportError("vertexai not installed. Install: pip install google-cloud-aiplatform")
        
        self.project_id = project_id or GOOGLE_CLOUD_PROJECT
        self.location = location or VERTEX_AI_LOCATION
        
        # Initialize Vertex AI
        try:
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"VertexAIAgentRegistry initialized: project={self.project_id}, location={self.location}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
        
        # In-memory cache for fast access (fallback if Vertex AI unavailable)
        self._local_registry: Dict[str, Dict[str, Any]] = {}
    
    def register_agent(
        self,
        agent_name: str,
        agent_url: str,
        agent_description: str,
        version: str = "1.0.0",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers agent in registry.
        
        Args:
            agent_name: Agent name (e.g., "kg_builder_agent")
            agent_url: Agent URL (e.g., "http://localhost:8002" or Cloud Run URL)
            agent_description: Agent description
            version: Agent version
            capabilities: List of agent capabilities
            metadata: Additional metadata
            
        Returns:
            Dictionary with registration result
        """
        try:
            agent_info = {
                "name": agent_name,
                "url": agent_url,
                "description": agent_description,
                "version": version,
                "capabilities": capabilities or [],
                "metadata": metadata or {},
                "registered_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            self._local_registry[agent_name] = agent_info
            
            # In production: register in Vertex AI Agent Builder
            # For this need to use Agent Engine deployment
            # After deployment agent is automatically registered in Agent Builder
            
            logger.info(f"Agent registered: {agent_name}", extra={
                "event_type": "agent_registered",
                "agent_name": agent_name,
                "agent_url": agent_url,
                "version": version
            })
            
            return {
                "status": "success",
                "agent_name": agent_name,
                "agent_info": agent_info
            }
        
        except Exception as e:
            logger.error(f"Error registering agent {agent_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def discover_agent(
        self,
        agent_name: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Discovers agent in registry.
        
        Args:
            agent_name: Agent name to search
            version: Agent version (optional, if None - latest version)
            
        Returns:
            Dictionary with agent information or None if not found
        """
        try:
            # First check local registry
            if agent_name in self._local_registry:
                agent_info = self._local_registry[agent_name]
                
                if version and agent_info.get("version") != version:
                    logger.warning(f"Version mismatch for {agent_name}: requested {version}, found {agent_info.get('version')}")
                    return None
                
                logger.debug(f"Agent discovered in local registry: {agent_name}", extra={
                    "event_type": "agent_discovered",
                    "agent_name": agent_name,
                    "source": "local_registry"
                })
                
                return agent_info
            
            # TODO: In production, search in Vertex AI Agent Builder via Agent Engine API
            
            logger.warning(f"Agent not found in registry: {agent_name}", extra={
                "event_type": "agent_not_found",
                "agent_name": agent_name
            })
            
            return None
        
        except Exception as e:
            logger.error(f"Error discovering agent {agent_name}: {e}", exc_info=True)
            return None
    
    def list_agents(
        self,
        filter_by_capability: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all registered agents.
        
        Args:
            filter_by_capability: Filter by capability (optional)
            
        Returns:
            List of dictionaries with agent information
        """
        try:
            agents = list(self._local_registry.values())
            
            # Filter by capability
            if filter_by_capability:
                agents = [
                    agent for agent in agents
                    if filter_by_capability in agent.get("capabilities", [])
                ]
            
            logger.debug(f"Listed {len(agents)} agents", extra={
                "event_type": "agents_listed",
                "count": len(agents),
                "filter": filter_by_capability
            })
            
            return agents
        
        except Exception as e:
            logger.error(f"Error listing agents: {e}", exc_info=True)
            return []
    
    def update_agent_status(
        self,
        agent_name: str,
        status: str
    ) -> bool:
        """Updates agent status.
        
        Args:
            agent_name: Agent name
            status: New status ("active", "inactive", "maintenance")
            
        Returns:
            True if updated successfully, False if agent not found
        """
        if agent_name not in self._local_registry:
            return False
        
        self._local_registry[agent_name]["status"] = status
        self._local_registry[agent_name]["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Agent status updated: {agent_name} -> {status}", extra={
            "event_type": "agent_status_updated",
            "agent_name": agent_name,
            "status": status
        })
        
        return True
    
    def get_agent_url(self, agent_name: str) -> Optional[str]:
        """Gets agent URL.
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent URL or None if not found
        """
        agent_info = self.discover_agent(agent_name)
        if agent_info:
            return agent_info.get("url")
        return None


# Global registry instance
_global_registry: Optional[VertexAIAgentRegistry] = None


def get_registry() -> VertexAIAgentRegistry:
    """Gets global registry instance.
    
    Returns:
        VertexAIAgentRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = VertexAIAgentRegistry()
    
    return _global_registry


def register_all_agents() -> Dict[str, Any]:
    """Registers all TabSage agents in registry.
    
    Returns:
        Dictionary with registration results
    """
    from config import (
        KG_BUILDER_A2A_URL,
        TOPIC_DISCOVERY_A2A_URL,
        SCRIPTWRITER_A2A_URL,
        GUEST_A2A_URL,
        AUDIO_PRODUCER_A2A_URL,
        EVALUATOR_A2A_URL,
        EDITOR_A2A_URL,
        PUBLISHER_A2A_URL
    )
    
    registry = get_registry()
    results = {}
    
    # Register all agents
    agents_to_register = [
        {
            "name": "kg_builder_agent",
            "url": KG_BUILDER_A2A_URL,
            "description": "KG Builder Agent - extracts entities and relationships from text",
            "capabilities": ["entity_extraction", "relation_extraction", "knowledge_graph"]
        },
        {
            "name": "topic_discovery_agent",
            "url": TOPIC_DISCOVERY_A2A_URL,
            "description": "Topic Discovery Agent - discovers topics for episodes",
            "capabilities": ["topic_discovery", "content_analysis"]
        },
        {
            "name": "scriptwriter_agent",
            "url": SCRIPTWRITER_A2A_URL,
            "description": "Scriptwriter Agent - generates podcast scripts",
            "capabilities": ["script_generation", "content_creation"]
        },
        {
            "name": "guest_agent",
            "url": GUEST_A2A_URL,
            "description": "Guest/Persona Agent - simulates guest based on KG",
            "capabilities": ["persona_simulation", "expert_qa"]
        },
        {
            "name": "audio_producer_agent",
            "url": AUDIO_PRODUCER_A2A_URL,
            "description": "Audio Producer Agent - creates audio from text",
            "capabilities": ["tts", "audio_production"]
        },
        {
            "name": "evaluator_agent",
            "url": EVALUATOR_A2A_URL,
            "description": "Evaluator Agent - evaluates text and audio quality",
            "capabilities": ["quality_evaluation", "text_evaluation", "audio_evaluation"]
        },
        {
            "name": "editor_agent",
            "url": EDITOR_A2A_URL,
            "description": "Editor Agent - human-in-the-loop review and editing",
            "capabilities": ["human_review", "content_editing"]
        },
        {
            "name": "publisher_agent",
            "url": PUBLISHER_A2A_URL,
            "description": "Publisher Agent - publishes podcasts to hosting platforms",
            "capabilities": ["publishing", "distribution"]
        }
    ]
    
    for agent_config in agents_to_register:
        result = registry.register_agent(
            agent_name=agent_config["name"],
            agent_url=agent_config["url"],
            agent_description=agent_config["description"],
            capabilities=agent_config["capabilities"]
        )
        results[agent_config["name"]] = result
    
    logger.info(f"Registered {len(results)} agents in registry", extra={
        "event_type": "all_agents_registered",
        "agents_count": len(results)
    })
    
    return results


def discover_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """Discovers agent in registry (convenience function).
    
    Args:
        agent_name: Agent name
        
    Returns:
        Dictionary with agent information or None
    """
    registry = get_registry()
    return registry.discover_agent(agent_name)

