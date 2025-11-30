"""
KG Builder Agent - entity and relationship extraction from text

This agent is responsible for building knowledge graph from processed text.
It extracts named entities (PERSON, ORGANIZATION, CONCEPT, EVENT, LOCATION)
and relationships between them, creating structured knowledge representation.

Architecture:
- Uses LlmAgent from Google ADK with Gemini API
- Processes each text chunk separately for accuracy
- Integrated with Knowledge Graph (Firestore or InMemory)
- Supports A2A for remote calls

Workflow:
1. Receives text chunks from Ingest Agent
2. For each chunk extracts entities and relationships via LLM
3. Normalizes and links entities (entity linking)
4. Saves to knowledge graph with confidence scores
5. Returns statistics of extracted data

Input:
- chunks: List of text chunks
- title: Article title
- language: Text language
- session_id, episode_id: For tracking

Output:
- entities: List of extracted entities
- relations: List of extracted relationships
- stats: Statistics (number of entities, relationships)
"""

import json
import logging
from typing import Dict, Any, Optional, List

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner, InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from tools.embeddings import generate_embeddings
from tools.ner_and_linking import link_entities, normalize_entity_name
from tools.kg_client import get_kg_instance
from schemas.models import (
    KGBuilderPayload, KGBuilderResponse, Entity, Relation, KGChunkExtraction
)
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def extract_entities_relations_llm(chunk_text: str, model: Gemini) -> Dict[str, Any]:
    """Extracts entities and relationships from chunk using LLM.
    
    Args:
        chunk_text: Chunk text
        model: Gemini model
        
    Returns:
        Dictionary with extraction results
    """
    system_prompt = """You are an Extractor for building Knowledge Graph. Input — single text chunk. Return list of entities (type, canonical_name, aliases), relationships (subject, predicate, object), confidence. Use strict JSON schema.

Return JSON in format:
{
  "entities": [
    {
      "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT|EVENT|...",
      "canonical_name": "canonical name",
      "aliases": ["alternative names"],
      "confidence": 0.0-1.0
    }
  ],
  "relations": [
    {
      "subject": "subject (canonical_name)",
      "predicate": "relationship type (WORKS_FOR, LOCATED_IN, CREATED, MENTIONED_IN, etc.)",
      "object": "object (canonical_name)",
      "confidence": 0.0-1.0
    }
  ]
}"""

    try:
        extractor_agent = LlmAgent(
            model=model,
            name="kg_extractor",
            instruction=system_prompt,
        )
        
        # Use Runner with session_service instead of InMemoryRunner
        session_service = InMemorySessionService()
        runner = Runner(
            agent=extractor_agent,
            app_name="extract",
            session_service=session_service
        )
        
        # Create session
        session_id = f"extract_{hash(chunk_text) % 10000}"
        session = await session_service.create_session(
            app_name="extract",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=f"CHUNK: {chunk_text}")]
            )
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        # Parse JSON from response
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        return {
            "status": "success",
            "entities": result.get("entities", []),
            "relations": result.get("relations", [])
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "status": "error",
            "error_message": f"JSON parse error: {e}",
            "entities": [],
            "relations": []
        }
    except Exception as e:
        logger.error(f"Error in extract_entities_relations_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "entities": [],
            "relations": []
        }


def create_kg_builder_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates KG Builder Agent.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for knowledge graph building
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    # Tools for graph work
    def add_entity_to_kg(entity: Dict[str, Any]) -> Dict[str, Any]:
        """Adds entity to knowledge graph.
        
        Args:
            entity: Dictionary with type, canonical_name, aliases, confidence
            
        Returns:
            Dictionary with operation result
        """
        kg = get_kg_instance()
        return kg.add_entity(entity)
    
    def add_relation_to_kg(relation: Dict[str, Any]) -> Dict[str, Any]:
        """Adds relationship to knowledge graph.
        
        Args:
            relation: Dictionary with subject, predicate, object, confidence
            
        Returns:
            Dictionary with operation result
        """
        kg = get_kg_instance()
        return kg.add_relation(relation)
    
    def get_kg_stats() -> Dict[str, Any]:
        """Gets knowledge graph statistics.
        
        Returns:
            Dictionary with statistics
        """
        kg = get_kg_instance()
        return kg.get_graph_stats()
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="kg_builder_agent",
        description="KG Builder Agent for TabSage - extracts entities and relationships, updates knowledge graph",
        instruction="""You are a KG Builder Agent for TabSage. Your task:

1. Accept text chunks from Ingest Agent
2. Extract entities and relationships from each chunk
3. Normalize and link entities (entity linking)
4. Add entities and relationships to knowledge graph using tools
5. Return extraction results

Use add_entity_to_kg to add entities.
Use add_relation_to_kg to add relationships.
Use get_kg_stats to check graph state.""",
        tools=[add_entity_to_kg, add_relation_to_kg, get_kg_stats],
    )
    
    return agent


@observe_agent("kg_builder_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Processes one payload through KG Builder Agent.
    
    Args:
        payload: Input data (chunks, title, language, session_id, episode_id)
        agent: KG Builder Agent (if None, creates new one)
        
    Returns:
        Dictionary with processing results in KGBuilderResponse format
    """
    try:
        # Try to get data from shared memory if use_shared_memory=True
        shared_mem = None
        use_shared_memory = True  # By default use shared memory
        if use_shared_memory:
            try:
                shared_mem = get_shared_memory()
                session_id = payload.get("session_id", "default")
                namespace = f"session_{session_id}"
                
                # Try to get ingest_result from shared memory
                ingest_result = shared_mem.get("ingest_result", namespace=namespace)
                if ingest_result and not payload.get("chunks"):
                    # Use data from shared memory
                    payload["chunks"] = ingest_result.get("chunks", [])
                    payload["title"] = ingest_result.get("title", payload.get("title", ""))
                    payload["language"] = ingest_result.get("language", payload.get("language", ""))
                    logger.info("Using data from shared memory", extra={
                        "event_type": "shared_memory_used",
                        "namespace": namespace
                    })
            except Exception as e:
                logger.debug(f"Could not use shared memory: {e}")
        
        # Validate payload
        kg_payload = KGBuilderPayload(**payload)
        
        # Create agent if not provided
        if agent is None:
            agent = create_kg_builder_agent()
        
        # Create runner and session
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        # Create session
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id=kg_payload.session_id
        )
        
        # Get knowledge graph
        kg = get_kg_instance()
        
        # Process each chunk
        all_entities = []
        all_relations = []
        chunk_extractions = []
        
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
        
        for idx, chunk in enumerate(kg_payload.chunks):
            logger.info(f"Processing chunk {idx + 1}/{len(kg_payload.chunks)}")
            
            # Extract entities and relationships via LLM
            extraction_result = await extract_entities_relations_llm(chunk, model)
            
            if extraction_result["status"] == "error":
                logger.warning(f"Failed to extract from chunk {idx}: {extraction_result.get('error_message')}")
                continue
            
            entities_data = extraction_result.get("entities", [])
            relations_data = extraction_result.get("relations", [])
            
            # Normalize and link entities
            linked_result = link_entities(entities_data)
            if linked_result["status"] == "success":
                entities_data = linked_result["linked_entities"]
            
            # Get article_url from payload metadata
            article_url = payload.get("metadata", {}).get("url") if isinstance(payload.get("metadata"), dict) else None
            
            # Add to graph with article information
            
            for entity_data in entities_data:
                # Add article information
                if article_url:
                    entity_data["article_url"] = article_url
                
                add_result = kg.add_entity(entity_data)
                if add_result["status"] == "success":
                    # Create Entity object for response
                    entity = Entity(
                        type=entity_data.get("type", "ENTITY"),
                        canonical_name=entity_data.get("canonical_name", ""),
                        aliases=entity_data.get("aliases", []),
                        confidence=entity_data.get("confidence", 0.5)
                    )
                    all_entities.append(entity)
            
            for relation_data in relations_data:
                # Add article information
                if article_url:
                    relation_data["article_url"] = article_url
                add_result = kg.add_relation(relation_data)
                if add_result["status"] == "success":
                    # Create Relation object for response
                    relation = Relation(
                        subject=relation_data.get("subject", ""),
                        predicate=relation_data.get("predicate", ""),
                        object=relation_data.get("object", ""),
                        confidence=relation_data.get("confidence", 0.5)
                    )
                    all_relations.append(relation)
            
            # Save extraction for this chunk
            chunk_extraction = KGChunkExtraction(
                entities=[Entity(**e) for e in entities_data],
                relations=[Relation(**r) for r in relations_data],
                chunk_text=chunk,
                chunk_index=idx
            )
            chunk_extractions.append(chunk_extraction)
        
        # Form response
        response = KGBuilderResponse(
            entities=all_entities,
            relations=all_relations,
            chunk_extractions=chunk_extractions,
            session_id=kg_payload.session_id,
            episode_id=kg_payload.episode_id,
            graph_updated=True
        )
        
        result_dict = response.dict()
        
        # Save result in shared memory for use by other agents
        if shared_mem:
            try:
                session_id = payload.get("session_id", kg_payload.session_id)
                namespace = f"session_{session_id}"
                shared_mem.set("kg_result", result_dict, namespace=namespace, ttl_seconds=3600)
                logger.info("KG result saved to shared memory", extra={
                    "event_type": "shared_memory_saved",
                    "namespace": namespace
                })
            except Exception as e:
                logger.debug(f"Could not save to shared memory: {e}")
        
        logger.info(f"Successfully processed {len(kg_payload.chunks)} chunks for session {kg_payload.session_id}")
        logger.info(f"Graph stats: {kg.get_graph_stats()}")
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

