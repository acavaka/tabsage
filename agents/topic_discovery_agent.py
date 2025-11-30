"""Topic Discovery Agent - analyzes graph and suggests topics for episodes"""

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
from schemas.models import (
    TopicDiscoveryPayload, TopicDiscoveryResponse, Topic
)
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def discover_topics_llm(graph_snapshot: Dict[str, Any], max_topics: int, model: Gemini) -> Dict[str, Any]:
    """Discovers topics using LLM based on graph snapshot.
    
    Args:
        graph_snapshot: Knowledge graph snapshot
        max_topics: Maximum number of topics
        model: Gemini model
        
    Returns:
        Dictionary with discovery results
    """
    system_prompt = """You are a Topic Discovery agent for TabSage. Input — graph snapshot (key nodes, their weights, recent_activity). Suggest up to 10 topics for episode. For each topic provide: title, why_it_matters (1-2 sentences), seed_nodes (list of nodes), difficulty (low/medium/high), estimated_length_minutes.

Return JSON in format:
{
  "topics": [
    {
      "title": "topic name",
      "why_it_matters": "why this matters (1-2 sentences)",
      "seed_nodes": ["node_id1", "node_id2"],
      "difficulty": "low|medium|high",
      "estimated_length_minutes": 15
    }
  ]
}"""

    try:
        nodes_info = []
        for node in graph_snapshot.get("nodes", [])[:50]:  # Take top 50 nodes
            nodes_info.append({
                "node_id": node.get("node_id", ""),
                "type": node.get("type", ""),
                "canonical_name": node.get("canonical_name", ""),
                "confidence": node.get("confidence", 0)
            })
        
        graph_description = f"""Graph Snapshot:
- Total nodes: {graph_snapshot.get('total_nodes', 0)}
- Total edges: {graph_snapshot.get('edges_count', 0)}
- Top nodes: {json.dumps(nodes_info, ensure_ascii=False, indent=2)}"""

        discovery_agent = LlmAgent(
            model=model,
            name="topic_discovery",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=discovery_agent,
            app_name="topic_discovery",
            session_service=session_service
        )
        
        session_id = f"discover_{hash(str(graph_snapshot)) % 10000}"
        session = await session_service.create_session(
            app_name="topic_discovery",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=graph_description)]
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
            "topics": result.get("topics", [])
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "topics": []
        }
    except Exception as e:
        logger.error(f"Error in discover_topics_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "topics": []
        }


def create_topic_discovery_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Topic Discovery Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for topic discovery
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    def get_graph_snapshot(limit: int = 100) -> Dict[str, Any]:
        """Gets knowledge graph snapshot.
        
        Args:
            limit: Maximum number of nodes
            
        Returns:
            Dictionary with graph snapshot
        """
        kg = get_kg_instance()
        return kg.get_snapshot(limit=limit)
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="topic_discovery_agent",
        description="Topic Discovery Agent for TabSage - analyzes graph and suggests topics for episodes",
        instruction="""You are a Topic Discovery Agent for TabSage. Your task:

1. Analyze knowledge graph via get_graph_snapshot
2. Identify interesting and relevant topics based on graph nodes
3. Suggest topics for podcast episodes
4. For each topic specify: title, why_it_matters, seed_nodes, difficulty, estimated_length_minutes

Use get_graph_snapshot to get current graph state.""",
        tools=[get_graph_snapshot],
    )
    
    return agent


@observe_agent("topic_discovery_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through Topic Discovery Agent.
    
    Args:
        payload: Input data (session_id, episode_id, max_topics, graph_snapshot)
        agent: Topic Discovery Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in TopicDiscoveryResponse format
    """
    try:
        # Validate payload
        discovery_payload = TopicDiscoveryPayload(**payload)
        
        # Create agent if not provided
        if agent is None:
            agent = create_topic_discovery_agent()
        
        kg = get_kg_instance()
        if discovery_payload.graph_snapshot:
            graph_snapshot = discovery_payload.graph_snapshot
        else:
            graph_snapshot = kg.get_snapshot(limit=100)
        
        graph_stats = kg.get_graph_stats()
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id=discovery_payload.session_id
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
        
        discovery_result = await discover_topics_llm(
            graph_snapshot,
            discovery_payload.max_topics,
            model
        )
        
        if discovery_result["status"] == "error":
            raise ValueError(discovery_result.get("error_message", "Unknown error"))
        
        topics = []
        for topic_data in discovery_result.get("topics", [])[:discovery_payload.max_topics]:
            try:
                topic = Topic(**topic_data)
                topics.append(topic)
            except Exception as e:
                logger.warning(f"Failed to create Topic from data: {e}")
                continue
        
        response = TopicDiscoveryResponse(
            topics=topics,
            session_id=discovery_payload.session_id,
            episode_id=discovery_payload.episode_id,
            graph_stats=graph_stats
        )
        
        logger.info(f"Discovered {len(topics)} topics for session {discovery_payload.session_id}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

