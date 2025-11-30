"""Orchestrator with full A2A support - coordination of all agents via A2A protocol"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from services.a2a.a2a_client import call_agent_via_a2a
from core.config import (
    KG_BUILDER_A2A_URL, TOPIC_DISCOVERY_A2A_URL, SCRIPTWRITER_A2A_URL,
    GUEST_A2A_URL, AUDIO_PRODUCER_A2A_URL, EVALUATOR_A2A_URL,
    EDITOR_A2A_URL, PUBLISHER_A2A_URL, get_config
)
from registry.integration import get_agent_url_from_registry
from schemas.models import (
    IngestPayload, KGBuilderPayload, TopicDiscoveryPayload,
    ScriptwriterPayload, AudioProducerPayload, EvaluatorPayload,
    EditorPayload, PublisherPayload
)

logger = logging.getLogger(__name__)


class EpisodeStatus(Enum):
    """Episode status in pipeline"""
    CREATED = "created"
    INGESTING = "ingesting"
    KG_BUILDING = "kg_building"
    TOPIC_DISCOVERING = "topic_discovering"
    SCRIPTWRITING = "scriptwriting"
    EDITING = "editing"
    AUDIO_PRODUCING = "audio_producing"
    EVALUATING = "evaluating"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EpisodeContext:
    """Episode context for state tracking"""
    episode_id: str
    session_id: str
    status: EpisodeStatus
    created_at: datetime
    updated_at: datetime
    data: Dict[str, Any]
    version: int = 1
    retry_count: int = 0
    max_retries: int = 3


class A2AOrchestrator:
    """Orchestrator for coordinating all TabSage agents via A2A protocol"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, use_a2a: bool = True):
        """Initialize A2A Orchestrator.
        
        Args:
            config: Configuration (optional)
            use_a2a: Use A2A for all calls (default: True)
        """
        self.config = config or get_config()
        self.episodes: Dict[str, EpisodeContext] = {}
        self.max_retries = self.config.get("max_retries", 3)
        self.enable_hitl = self.config.get("enable_hitl", True)
        self.use_a2a = use_a2a
    
    def create_episode(self, episode_id: str, session_id: str) -> EpisodeContext:
        """Creates new episode context."""
        context = EpisodeContext(
            episode_id=episode_id,
            session_id=session_id,
            status=EpisodeStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            data={},
            version=1
        )
        self.episodes[episode_id] = context
        logger.info(f"Created episode context: {episode_id}")
        return context
    
    def update_episode_status(self, episode_id: str, status: EpisodeStatus, data: Optional[Dict[str, Any]] = None):
        """Updates episode status."""
        context = self.episodes.get(episode_id)
        if context:
            context.status = status
            context.updated_at = datetime.now()
            if data:
                context.data.update(data)
            logger.info(f"Episode {episode_id} status: {status.value}")
    
    async def run_pipeline(
        self,
        raw_text: str,
        episode_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        skip_steps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Runs full pipeline via A2A.
        
        Args:
            raw_text: Raw text for processing
            episode_id: Episode identifier
            session_id: Session identifier
            metadata: Additional metadata
            skip_steps: List of steps to skip
            
        Returns:
            Dictionary with results of entire pipeline
        """
        if skip_steps is None:
            skip_steps = []
        
        context = self.create_episode(episode_id, session_id)
        results = {}
        
        try:
            # Step 1: Ingest (currently without A2A, as this is input agent)
            if "ingest" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.INGESTING)
                from agents.ingest_agent import run_once as ingest_run_once
                ingest_payload = IngestPayload(
                    raw_text=raw_text,
                    metadata=metadata or {},
                    session_id=session_id,
                    episode_id=episode_id
                )
                ingest_result = await ingest_run_once(ingest_payload.dict())
                if "error_message" in ingest_result:
                    raise Exception(f"Ingest failed: {ingest_result['error_message']}")
                results["ingest"] = ingest_result
                context.data["ingest"] = ingest_result
            
            # Step 2: KG Builder via A2A
            if "kg_builder" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.KG_BUILDING)
                kg_payload = {
                    "chunks": results["ingest"].get("chunks", []),
                    "title": results["ingest"].get("title", ""),
                    "language": results["ingest"].get("language", ""),
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                kg_url = get_agent_url_from_registry("kg_builder_agent", fallback_url=KG_BUILDER_A2A_URL)
                kg_result = await call_agent_via_a2a(
                    agent_url=kg_url,
                    agent_name="kg_builder_agent",
                    agent_description="KG Builder Agent for extracting entities and relations",
                    payload=kg_payload,
                    session_id=session_id
                )
                if kg_result.get("status") != "success":
                    raise Exception(f"KG Builder failed: {kg_result.get('error_message')}")
                results["kg_builder"] = kg_result.get("result", {})
                context.data["kg_builder"] = results["kg_builder"]
            
            # Step 3: Topic Discovery via A2A
            if "topic_discovery" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.TOPIC_DISCOVERING)
                topic_payload = {
                    "session_id": session_id,
                    "episode_id": episode_id,
                    "max_topics": 5
                }
                topic_url = get_agent_url_from_registry("topic_discovery_agent", fallback_url=TOPIC_DISCOVERY_A2A_URL)
                topic_result = await call_agent_via_a2a(
                    agent_url=topic_url,
                    agent_name="topic_discovery_agent",
                    agent_description="Topic Discovery Agent for discovering podcast topics",
                    payload=topic_payload,
                    session_id=session_id
                )
                if topic_result.get("status") != "success":
                    raise Exception(f"Topic Discovery failed: {topic_result.get('error_message')}")
                results["topic_discovery"] = topic_result.get("result", {})
                context.data["topic_discovery"] = results["topic_discovery"]
            
            # Step 4: Scriptwriter via A2A
            if "scriptwriter" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.SCRIPTWRITING)
                topics = results["topic_discovery"].get("topics", [])
                if not topics:
                    raise Exception("No topics discovered")
                
                script_payload = {
                    "topic": topics[0] if isinstance(topics[0], dict) else topics[0].dict(),
                    "target_audience": "General audience",
                    "format": "informative",
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                script_url = get_agent_url_from_registry("scriptwriter_agent", fallback_url=SCRIPTWRITER_A2A_URL)
                script_result = await call_agent_via_a2a(
                    agent_url=script_url,
                    agent_name="scriptwriter_agent",
                    agent_description="Scriptwriter Agent for generating podcast scripts",
                    payload=script_payload,
                    session_id=session_id
                )
                if script_result.get("status") != "success":
                    raise Exception(f"Scriptwriter failed: {script_result.get('error_message')}")
                results["scriptwriter"] = script_result.get("result", {})
                context.data["scriptwriter"] = results["scriptwriter"]
            
            # Step 5: Editor via A2A (human-in-loop)
            if "editor" not in skip_steps and self.enable_hitl:
                self.update_episode_status(episode_id, EpisodeStatus.EDITING)
                editor_payload = {
                    "script": results["scriptwriter"],
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                editor_url = get_agent_url_from_registry("editor_agent", fallback_url=EDITOR_A2A_URL)
                editor_result = await call_agent_via_a2a(
                    agent_url=editor_url,
                    agent_name="editor_agent",
                    agent_description="Editor Agent for human-in-loop review",
                    payload=editor_payload,
                    session_id=session_id
                )
                if editor_result.get("status") != "success":
                    raise Exception(f"Editor failed: {editor_result.get('error_message')}")
                results["editor"] = editor_result.get("result", {})
                context.data["editor"] = results["editor"]
            
            # Step 6: Audio Producer via A2A
            if "audio_producer" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.AUDIO_PRODUCING)
                audio_payload = {
                    "segments": results["scriptwriter"].get("segments", []),
                    "full_script": results["scriptwriter"].get("full_script", ""),
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                audio_url = get_agent_url_from_registry("audio_producer_agent", fallback_url=AUDIO_PRODUCER_A2A_URL)
                audio_result = await call_agent_via_a2a(
                    agent_url=audio_url,
                    agent_name="audio_producer_agent",
                    agent_description="Audio Producer Agent for TTS and audio production",
                    payload=audio_payload,
                    session_id=session_id
                )
                if audio_result.get("status") != "success":
                    raise Exception(f"Audio Producer failed: {audio_result.get('error_message')}")
                results["audio_producer"] = audio_result.get("result", {})
                context.data["audio_producer"] = results["audio_producer"]
            
            # Step 7: Evaluator via A2A
            if "evaluator" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.EVALUATING)
                evaluator_payload = {
                    "content_type": "audio",
                    "content": results["audio_producer"],
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                evaluator_url = get_agent_url_from_registry("evaluator_agent", fallback_url=EVALUATOR_A2A_URL)
                evaluator_result = await call_agent_via_a2a(
                    agent_url=evaluator_url,
                    agent_name="evaluator_agent",
                    agent_description="Evaluator Agent for quality assessment",
                    payload=evaluator_payload,
                    session_id=session_id
                )
                if evaluator_result.get("status") != "success":
                    raise Exception(f"Evaluator failed: {evaluator_result.get('error_message')}")
                results["evaluator"] = evaluator_result.get("result", {})
                context.data["evaluator"] = results["evaluator"]
            
            # Step 8: Publisher via A2A
            if "publisher" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.PUBLISHING)
                publisher_payload = {
                    "audio_file_path": results["audio_producer"].get("audio_file_path", ""),
                    "metadata": {
                        "title": results["ingest"].get("title", ""),
                        "description": results["scriptwriter"].get("summary", ""),
                        "episode_id": episode_id
                    },
                    "session_id": session_id,
                    "episode_id": episode_id
                }
                publisher_url = get_agent_url_from_registry("publisher_agent", fallback_url=PUBLISHER_A2A_URL)
                publisher_result = await call_agent_via_a2a(
                    agent_url=publisher_url,
                    agent_name="publisher_agent",
                    agent_description="Publisher Agent for publishing episodes",
                    payload=publisher_payload,
                    session_id=session_id
                )
                if publisher_result.get("status") != "success":
                    raise Exception(f"Publisher failed: {publisher_result.get('error_message')}")
                results["publisher"] = publisher_result.get("result", {})
                context.data["publisher"] = results["publisher"]
            
            # Completion
            self.update_episode_status(episode_id, EpisodeStatus.COMPLETED)
            results["episode_id"] = episode_id
            results["session_id"] = session_id
            results["status"] = "completed"
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed for episode {episode_id}: {e}", exc_info=True)
            self.update_episode_status(episode_id, EpisodeStatus.FAILED)
            return {
                "episode_id": episode_id,
                "session_id": session_id,
                "status": "failed",
                "error_message": str(e),
                "results": results
            }

