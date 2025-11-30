"""
Orchestrator - coordination of all agents in pipeline

Orchestrator is the central component that coordinates the work
of all agents in the system. It manages execution sequence,
handles errors, and ensures proper data transfer between agents.

Architecture:
- Coordinates sequential pipeline: Ingest → KG Builder → Summary
- Supports parallel execution of independent tasks
- Handles errors with fallback mechanisms
- Integrated with A2A for remote agents
- Uses session_id and episode_id for tracking

Workflow:
1. Ingest Agent: normalization and chunking
2. KG Builder Agent: knowledge extraction (can run in parallel)
3. Summary Agent: summary generation
4. Save to Firestore
5. Send result to user

Features:
- Idempotency: safe for repeated runs
- Error handling: graceful degradation
- Logging all stages for observability
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.topic_discovery_agent import run_once as topic_discovery_run_once
from agents.scriptwriter_agent import run_once as scriptwriter_run_once
from agents.audio_producer_agent import run_once as audio_producer_run_once
from agents.evaluator_agent import run_once as evaluator_run_once
from agents.editor_agent import run_once as editor_run_once
from agents.publisher_agent import run_once as publisher_run_once
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
    data: Dict[str, Any]  # Intermediate data between agents
    version: int = 1
    retry_count: int = 0
    max_retries: int = 3


class Orchestrator:
    """Orchestrator for coordinating all TabSage agents"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Orchestrator.
        
        Args:
            config: Configuration (optional)
        """
        self.config = config or {}
        self.episodes: Dict[str, EpisodeContext] = {}  # episode_id -> context
        self.max_retries = self.config.get("max_retries", 3)
        self.enable_hitl = self.config.get("enable_hitl", True)  # Human-in-the-loop
    
    def create_episode(self, episode_id: str, session_id: str) -> EpisodeContext:
        """Creates new episode context.
        
        Args:
            episode_id: Episode identifier
            session_id: Session identifier
            
        Returns:
            EpisodeContext
        """
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
    
    def get_episode(self, episode_id: str) -> Optional[EpisodeContext]:
        """Gets episode context.
        
        Args:
            episode_id: Episode identifier
            
        Returns:
            EpisodeContext or None
        """
        return self.episodes.get(episode_id)
    
    def update_episode_status(self, episode_id: str, status: EpisodeStatus, data: Optional[Dict[str, Any]] = None):
        """Updates episode status.
        
        Args:
            episode_id: Episode identifier
            status: New status
            data: Data to save (optional)
        """
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
        """Runs full podcast creation pipeline.
        
        Args:
            raw_text: Raw text for processing
            episode_id: Episode identifier
            session_id: Session identifier
            metadata: Additional metadata
            skip_steps: List of steps to skip (optional)
            
        Returns:
            Dictionary with results of entire pipeline
        """
        if skip_steps is None:
            skip_steps = []
        
        context = self.create_episode(episode_id, session_id)
        results = {}
        
        try:
            # Step 1: Ingest
            if "ingest" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.INGESTING)
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
            
            # Step 2: KG Builder
            if "kg_builder" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.KG_BUILDING)
                kg_payload = KGBuilderPayload(
                    chunks=results["ingest"].get("chunks", []),
                    title=results["ingest"].get("title", ""),
                    language=results["ingest"].get("language", ""),
                    session_id=session_id,
                    episode_id=episode_id
                )
                kg_result = await kg_builder_run_once(kg_payload.dict())
                if "error_message" in kg_result:
                    raise Exception(f"KG Builder failed: {kg_result['error_message']}")
                results["kg_builder"] = kg_result
                context.data["kg_builder"] = kg_result
            
            # Step 3: Topic Discovery
            if "topic_discovery" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.TOPIC_DISCOVERING)
                topic_payload = TopicDiscoveryPayload(
                    session_id=session_id,
                    episode_id=episode_id,
                    max_topics=5
                )
                topic_result = await topic_discovery_run_once(topic_payload.dict())
                if "error_message" in topic_result:
                    raise Exception(f"Topic Discovery failed: {topic_result['error_message']}")
                results["topic_discovery"] = topic_result
                context.data["topic_discovery"] = topic_result
            
            # Step 4: Scriptwriter
            if "scriptwriter" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.SCRIPTWRITING)
                topics = results["topic_discovery"].get("topics", [])
                if not topics:
                    raise Exception("No topics discovered")
                
                from schemas.models import Topic
                selected_topic = Topic(**topics[0])
                
                script_payload = ScriptwriterPayload(
                    topic=selected_topic.dict(),
                    target_audience="General audience",
                    format="informative",
                    session_id=session_id,
                    episode_id=episode_id
                )
                script_result = await scriptwriter_run_once(script_payload.dict())
                if "error_message" in script_result:
                    raise Exception(f"Scriptwriter failed: {script_result['error_message']}")
                results["scriptwriter"] = script_result
                context.data["scriptwriter"] = script_result
            
            # Step 5: Editor (human-in-loop)
            if "editor" not in skip_steps and self.enable_hitl:
                self.update_episode_status(episode_id, EpisodeStatus.EDITING)
                # Convert dict to ScriptwriterResponse if needed
                script_data = results["scriptwriter"]
                if isinstance(script_data, dict):
                    from schemas.models import ScriptwriterResponse
                    script_data = ScriptwriterResponse(**script_data)
                
                editor_payload = EditorPayload(
                    script=script_data.dict() if hasattr(script_data, 'dict') else script_data,
                    session_id=session_id,
                    episode_id=episode_id
                )
                editor_result = await editor_run_once(editor_payload.dict(), auto_approve=True)
                if "error_message" in editor_result:
                    raise Exception(f"Editor failed: {editor_result['error_message']}")
                results["editor"] = editor_result
                context.data["editor"] = editor_result
                
                # If not approved, can return to Scriptwriter
                if not editor_result.get("approved", False):
                    logger.warning(f"Script not approved for episode {episode_id}")
            
            # Step 6: Audio Producer
            if "audio_producer" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.AUDIO_PRODUCING)
                audio_payload = AudioProducerPayload(
                    segments=results["scriptwriter"].get("segments", []),
                    full_script=results["scriptwriter"].get("full_script", ""),
                    session_id=session_id,
                    episode_id=episode_id
                )
                audio_result = await audio_producer_run_once(audio_payload.dict())
                if "error_message" in audio_result:
                    raise Exception(f"Audio Producer failed: {audio_result['error_message']}")
                results["audio_producer"] = audio_result
                context.data["audio_producer"] = audio_result
            
            # Step 7: Evaluator
            if "evaluator" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.EVALUATING)
                eval_payload = EvaluatorPayload(
                    text=results["scriptwriter"].get("full_script", ""),
                    session_id=session_id,
                    episode_id=episode_id
                )
                eval_result = await evaluator_run_once(eval_payload.dict())
                if "error_message" in eval_result:
                    logger.warning(f"Evaluator failed: {eval_result['error_message']}")
                else:
                    results["evaluator"] = eval_result
                    context.data["evaluator"] = eval_result
            
            # Step 8: Publisher
            if "publisher" not in skip_steps:
                self.update_episode_status(episode_id, EpisodeStatus.PUBLISHING)
                pub_payload = PublisherPayload(
                    script=results["scriptwriter"],
                    audio_file_path=None,  # In production this will be real path
                    session_id=session_id,
                    episode_id=episode_id
                )
                pub_result = await publisher_run_once(pub_payload.dict())
                if "error_message" in pub_result:
                    raise Exception(f"Publisher failed: {pub_result['error_message']}")
                results["publisher"] = pub_result
                context.data["publisher"] = pub_result
            
            # Completion
            self.update_episode_status(episode_id, EpisodeStatus.COMPLETED)
            results["status"] = "completed"
            results["episode_id"] = episode_id
            results["session_id"] = session_id
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed for episode {episode_id}: {e}", exc_info=True)
            self.update_episode_status(episode_id, EpisodeStatus.FAILED)
            context.retry_count += 1
            
            # Retry logic
            if context.retry_count < self.max_retries:
                logger.info(f"Retrying episode {episode_id} (attempt {context.retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(2 ** context.retry_count)  # Exponential backoff
                return await self.run_pipeline(raw_text, episode_id, session_id, metadata, skip_steps)
            else:
                return {
                    "status": "failed",
                    "error_message": str(e),
                    "episode_id": episode_id,
                    "session_id": session_id
                }
    
    def get_episode_history(self, episode_id: str) -> Dict[str, Any]:
        """Gets episode processing history.
        
        Args:
            episode_id: Episode identifier
            
        Returns:
            Dictionary with history
        """
        context = self.episodes.get(episode_id)
        if not context:
            return {"error": "Episode not found"}
        
        return {
            "episode_id": context.episode_id,
            "session_id": context.session_id,
            "status": context.status.value,
            "version": context.version,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "retry_count": context.retry_count,
            "data_keys": list(context.data.keys())
        }

