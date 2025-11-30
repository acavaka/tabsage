"""Intent Recognition Agent - determines user intent in Telegram bot"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import re

from core.config import GEMINI_MODEL, get_config
from observability.logging import get_logger

logger = get_logger(__name__)


class UserIntent:
    """User intent types"""
    PROCESS_URL = "process_url"
    SEARCH_DATABASE = "search_database"
    GET_SOURCES = "get_sources"
    GENERATE_AUDIO = "generate_audio"
    UNKNOWN = "unknown"


def is_url(text: str) -> bool:
    """Checks if text is a URL"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return bool(url_pattern.match(text.strip()))


async def recognize_intent_llm(
    user_message: str,
    model: Gemini
) -> Dict[str, Any]:
    """Recognizes user intent using LLM.
    
    Args:
        user_message: User message
        model: Gemini model
        
    Returns:
        Dictionary with intent and parameters
    """
    # Quick URL check
    if is_url(user_message):
        return {
            "intent": UserIntent.PROCESS_URL,
            "url": user_message.strip(),
            "confidence": 1.0
        }
    
    system_prompt = """You are an Intent Recognition Agent for TabSage Telegram bot.

Determine user intent from following types:
1. process_url - user wants to process new article (sent URL or asks to process link)
2. search_database - user searches something in database (asks question, searches topic, material)
3. get_sources - user asks to show all sources/articles on topic
4. generate_audio - user wants to get audio version (asks for audio, podcast, voiceover)

Return strictly JSON in format:
{
  "intent": "process_url|search_database|get_sources|generate_audio|unknown",
  "confidence": 0.0-1.0,
  "parameters": {
    "url": "if process_url",
    "query": "if search_database",
    "topic": "if get_sources",
    "article_id": "if generate_audio"
  }
}"""

    try:
        intent_agent = LlmAgent(
            model=model,
            name="intent_agent",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=intent_agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id="intent_session"
        )
        
        user_prompt = f"Determine user intent: {user_message}"
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_prompt)]
            )
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        
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
            return result
        except json.JSONDecodeError:
            # Fallback: simple analysis
            message_lower = user_message.lower()
            if any(word in message_lower for word in ["find", "search", "look for"]):
                return {"intent": UserIntent.SEARCH_DATABASE, "confidence": 0.8, "parameters": {"query": user_message}}
            elif any(word in message_lower for word in ["audio", "voice", "podcast", "listen"]):
                return {"intent": UserIntent.GENERATE_AUDIO, "confidence": 0.8, "parameters": {}}
            else:
                return {"intent": UserIntent.UNKNOWN, "confidence": 0.5, "parameters": {}}
                
    except Exception as e:
        logger.error(f"Error in recognize_intent_llm: {e}")
        return {"intent": UserIntent.UNKNOWN, "confidence": 0.0, "parameters": {}, "error": str(e)}


async def recognize_intent(user_message: str) -> Dict[str, Any]:
    """Recognizes user intent.
    
    Args:
        user_message: User message
        
    Returns:
        Dictionary with intent and parameters
    """
    config = get_config()
    model = Gemini(
        model=config.get("gemini_model", GEMINI_MODEL),
        retry_options=types.HttpRetryOptions(
            attempts=2,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504]
        )
    )
    
    return await recognize_intent_llm(user_message, model)

