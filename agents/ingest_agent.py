"""
Ingest Agent - text normalization, chunking, summary generation

This agent is the first in the article processing pipeline. It is responsible for:
1. Normalizing raw text (removing extra characters, formatting)
2. Splitting text into chunks (maximum 5 segments)
3. Detecting text language
4. Generating basic summary

Architecture:
- Uses LlmAgent from Google ADK
- Integrated with Gemini API for LLM operations
- Supports A2A communication for interaction with other agents
- Idempotent - safe for repeated runs

Input:
- raw_text: Raw article text
- metadata: Metadata (url, title, source)
- session_id: Session ID for tracking
- episode_id: Episode/article ID

Output:
- title: Article title
- language: Detected language (ru, en, etc.)
- cleaned_text: Normalized text
- summary: Brief summary
- chunks: List of chunks (up to 5)
"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner, InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config, INGEST_CONFIG
from tools.nlp import chunk_text, clean_text, detect_language
from schemas.models import IngestPayload, IngestResponse
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def normalize_text_with_llm(raw_text: str, model: Gemini) -> Dict[str, Any]:
    """Normalizes text using LLM according to architecture prompt.
    
    Args:
        raw_text: Raw text to normalize
        model: Gemini model to use
        
    Returns:
        Dictionary with normalization results
        Success: {"status": "success", "title": ..., "language": ..., "cleaned_text": ..., "summary": ..., "chunks": [...]}
        Error: {"status": "error", "error_message": "..."}
    """
    system_prompt = """You are a Text Normalizer for TabSage. Your task is to take raw text (article, transcript) and return: title, language, cleaned_text (without ad markers), short_summary (1-2 sentences), suggested_chunks (<= 5). JSON format.

IMPORTANT: If article language is Russian, summary must be in Russian. If English - in English.

Return strictly JSON in format:
{
  "title": "title",
  "language": "ru or en",
  "cleaned_text": "cleaned text",
  "summary": "brief summary 1-2 sentences in article's language (Russian if ru, English if en)",
  "chunks": ["chunk1", "chunk2", ...]
}"""

    try:
        # Create temporary agent for normalization
        normalizer_agent = LlmAgent(
            model=model,
            name="text_normalizer",
            instruction=system_prompt,
        )
        
        # Use Runner with session_service
        session_service = InMemorySessionService()
        runner = Runner(
            agent=normalizer_agent,
            app_name="normalize",
            session_service=session_service
        )
        
        # Create session
        session_id = f"normalize_{hash(raw_text) % 10000}"
        session = await session_service.create_session(
            app_name="normalize",
            user_id="system",
            session_id=session_id
        )
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=raw_text)]
            )
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        # Parse JSON from response
        # LLM may return JSON in markdown code block or plain text
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        return {
            "status": "success",
            "title": result.get("title", ""),
            "language": result.get("language", "unknown"),
            "cleaned_text": result.get("cleaned_text", ""),
            "summary": result.get("summary", ""),
            "chunks": [
                ch.get("text", ch) if isinstance(ch, dict) else ch 
                for ch in result.get("chunks", [])
            ]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Fallback: use simple tools
        return {
            "status": "fallback",
            "title": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text,
            "language": detect_language(raw_text),
            "cleaned_text": clean_text(raw_text),
            "summary": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
            "chunks": [
                ch.get("text", ch) if isinstance(ch, dict) else ch 
                for ch in chunk_text(clean_text(raw_text))["chunks"]
            ]
        }
    except Exception as e:
        logger.error(f"Error in normalize_text_with_llm: {e}")
        return {
            "status": "error",
            "error_message": str(e)
        }


def create_ingest_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Ingest Agent with tools for normalization and chunking.
    
    Args:
        config: Agent configuration (optional)
        
    Returns:
        LlmAgent configured for ingest
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    # Tools for chunking (use settings from config)
    ingest_config = config.get("ingest", INGEST_CONFIG)
    default_max_chunks = ingest_config.get("max_chunks", 20)
    default_chunk_size = ingest_config.get("chunk_size", 5000)
    default_overlap = ingest_config.get("chunk_overlap", 500)
    
    def chunk_text_tool(text: str, max_chunks: Optional[int] = None) -> Dict[str, Any]:
        """Splits text into chunks.
        
        Args:
            text: Text to split
            max_chunks: Maximum number of chunks (default from config: 20)
            
        Returns:
            Dictionary with chunking results
        """
        if max_chunks is None:
            max_chunks = default_max_chunks
        return chunk_text(
            text, 
            max_chunks=max_chunks,
            chunk_size=default_chunk_size,
            overlap=default_overlap
        )
    
    # Create agent
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="ingest_agent",
        description="Ingest Agent for TabSage - normalizes text, chunks and prepares data for KG Builder",
        instruction=f"""You are an Ingest Agent for TabSage. Your task:

1. Accept raw text (article, transcript)
2. Normalize text (remove ads, markers)
3. Split into chunks (maximum {default_max_chunks}) using chunk_text_tool
4. Generate brief summary (1-2 sentences)
5. Detect text language
6. Extract or generate title

Always use chunk_text_tool to split text into chunks.
Return result in structured JSON format.""",
        tools=[chunk_text_tool],
    )
    
    return agent


@observe_agent("ingest_agent")
async def run_once(
    payload: Dict[str, Any],
    agent: Optional[LlmAgent] = None,
    kg_builder_url: Optional[str] = None
) -> Dict[str, Any]:
    """Processes one payload through Ingest Agent.
    
    Args:
        payload: Input data (raw_text, metadata, session_id, episode_id)
        agent: Ingest Agent (if None, creates new one)
        kg_builder_url: KG Builder Agent URL for A2A (optional, mock for now)
        
    Returns:
        Dictionary with processing results in IngestResponse format
    """
    try:
        # Validate payload
        ingest_payload = IngestPayload(**payload)
        
        # Create agent if not provided
        if agent is None:
            agent = create_ingest_agent()
        
        # Create runner and session
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        # Create session (async)
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id=ingest_payload.session_id
        )
        
        # Form request to agent
        user_message = f"""Process the following text:

{ingest_payload.raw_text}

Metadata: {json.dumps(ingest_payload.metadata, ensure_ascii=False)}
Episode ID: {ingest_payload.episode_id or 'N/A'}

Return result in JSON format with fields: title, language, cleaned_text, summary, chunks (maximum 5)."""
        
        # Run agent
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=ingest_payload.session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
        # Parse agent response
        # Try to extract JSON from response
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: use direct LLM normalization
            logger.warning("Agent response is not valid JSON, using direct LLM normalization")
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
            result = await normalize_text_with_llm(ingest_payload.raw_text, model)
            if result["status"] == "error":
                raise ValueError(result["error_message"])
            result = {
                "title": result["title"],
                "language": result["language"],
                "cleaned_text": result["cleaned_text"],
                "summary": result["summary"],
                "chunks": result["chunks"]
            }
        
        # Process chunks - can be dictionaries or strings
        chunks_raw = result.get("chunks", [])
        chunks_processed = []
        for chunk in chunks_raw[:5]:  # Limit to 5 chunks
            if isinstance(chunk, dict):
                # If chunk is dictionary, extract text
                chunk_text = chunk.get("text", chunk.get("chunk", ""))
                if chunk_text:
                    chunks_processed.append(chunk_text)
            elif isinstance(chunk, str):
                chunks_processed.append(chunk)
        
        # If chunks are empty, use fallback
        if not chunks_processed:
            cleaned = result.get("cleaned_text", ingest_payload.raw_text)
            chunks_fallback = chunk_text(cleaned)["chunks"]
            # Extract text from dictionaries if needed
            chunks_processed = [
                ch.get("text", ch) if isinstance(ch, dict) else ch 
                for ch in chunks_fallback[:5]
            ]
        
        # Form response
        response = IngestResponse(
            title=result.get("title", ""),
            language=result.get("language", "unknown"),
            cleaned_text=result.get("cleaned_text", ""),
            summary=result.get("summary", ""),
            chunks=chunks_processed,
            session_id=ingest_payload.session_id,
            episode_id=ingest_payload.episode_id
        )
        
        if kg_builder_url:
            logger.info(f"KG Builder URL configured: {kg_builder_url}")
            # Note: A2A integration is available via ingest_agent_a2a.py
        
        logger.info(f"Successfully processed ingest for session {ingest_payload.session_id}")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in run_once: {e}", exc_info=True)
        return {
            "status": "error",
            "error_message": str(e),
            "session_id": payload.get("session_id", "unknown"),
            "episode_id": payload.get("episode_id")
        }

