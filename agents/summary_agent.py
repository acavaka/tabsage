"""
Summary Agent - summary generation with intents and values

This agent generates structured article summary, extracting:
- Explanatory summary (2-3 paragraphs)
- Key points
- Intents - what author wants to convey
- Values - what values are promoted
- Trends - current trends in article
- Unusual points - what makes article stand out

Architecture:
- Uses Gemini API directly for generation
- Structured output via JSON
- Optimized for fast generation
- Integrated with Telegram bot for sending to user

Features:
- Focus on "intents and values" as required in task
- Brief but informative summary
- Structured format for further processing

Input:
- article_text: Article text (may be limited to 5000 characters)
- title: Article title
- url: Article URL for links

Output:
- summary: Explanatory summary
- key_points: List of key points
- intents: List of intents
- values: List of values
- trends: List of trends
- unusual_points: List of unusual points
"""

import json
import logging
from typing import Dict, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import GEMINI_MODEL, get_config
from observability.logging import get_logger
from observability.integration import observe_agent

logger = get_logger(__name__)


async def generate_summary_llm(
    article_text: str,
    title: str,
    url: str,
    model: Gemini
) -> Dict[str, Any]:
    """Generates summary with intents and values using LLM.
    
    Args:
        article_text: Article text
        title: Article title
        url: Article URL
        model: Gemini model
        
    Returns:
        Dictionary with summary, intents, values and key points
    """
    system_prompt = """You are a Summary Agent for TabSage. Your task is to create a brief summary from article with:
1. Key points (interesting, unusual, trending, useful)
2. Intents (what author wants to convey, main idea)
3. Values (key values and ideas)
4. Brief explanatory summary (2-3 paragraphs)

IMPORTANT: All output must be in Russian language.

Return strictly JSON in format:
{
  "summary": "brief explanatory summary 2-3 paragraphs in Russian",
  "key_points": [
    "key point 1 in Russian",
    "key point 2 in Russian",
    "key point 3 in Russian"
  ],
  "intents": [
    "intent 1 in Russian - what author wants to convey",
    "intent 2 in Russian"
  ],
  "values": [
    "value 1 in Russian - key idea",
    "value 2 in Russian"
  ],
  "trends": [
    "trend 1 in Russian - current topic",
    "trend 2 in Russian"
  ],
  "unusual_points": [
    "unusual point 1 in Russian",
    "unusual point 2 in Russian"
  ]
}"""

    try:
        summary_agent = LlmAgent(
            model=model,
            name="summary_agent",
            instruction=system_prompt,
        )
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=summary_agent,
            app_name="tabsage",
            session_service=session_service
        )
        
        session = await session_service.create_session(
            app_name="tabsage",
            user_id="system",
            session_id="summary_session"
        )
        
        user_message = f"""Analyze the following article and create summary in Russian language:

Title: {title}
URL: {url}

Article text:
{article_text[:5000]}  # Limit for token economy

Return JSON with summary, key_points, intents, values, trends and unusual_points. All content must be in Russian language."""
        
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
            result["url"] = url
            result["title"] = title
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from summary response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            # Fallback: return structured response
            return {
                "summary": response_text[:500],
                "key_points": [],
                "intents": [],
                "values": [],
                "trends": [],
                "unusual_points": [],
                "url": url,
                "title": title,
                "error": "Failed to parse JSON"
            }
            
    except Exception as e:
        logger.error(f"Error in generate_summary_llm: {e}", exc_info=True)
        return {
            "summary": f"Error generating summary: {str(e)}",
            "key_points": [],
            "intents": [],
            "values": [],
            "url": url,
            "title": title,
            "error": str(e)
        }


def create_summary_agent(config: Optional[Dict[str, Any]] = None) -> LlmAgent:
    """Creates Summary Agent.
    
    Args:
        config: Configuration (optional)
        
    Returns:
        LlmAgent for summary generation
    """
    if config is None:
        config = get_config()
    
    retry_config = types.HttpRetryOptions(
        attempts=3,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504]
    )
    
    agent = LlmAgent(
        model=Gemini(model=config.get("gemini_model", GEMINI_MODEL), retry_options=retry_config),
        name="summary_agent",
        description="Generates summaries with intents and values from articles",
        instruction="""You are a Summary Agent for TabSage. Generate brief summaries from articles with intents and values. All output must be in Russian language.""",
    )
    
    return agent


# Note: summary_agent has different signature, so we don't use @observe_agent
# Instead, add observability manually inside the function
async def run_once(
    article_text: str,
    title: str,
    url: str,
    agent: Optional[LlmAgent] = None
) -> Dict[str, Any]:
    """Generates summary from article.
    
    Args:
        article_text: Article text
        title: Article title
        url: Article URL
        agent: Summary Agent (if None, creates new one)
        
    Returns:
        Dictionary with summary, intents, values and key points
    """
    from observability.tracing import trace_span
    import time
    
    start_time = time.time()
    session_id = f"summary_{hash(url) % 10000}"
    
    logger.agent_start("summary_agent", session_id, {"title": title, "url": url})
    
    try:
        with trace_span("agent.summary_agent", {"agent.name": "summary_agent", "session.id": session_id}):
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
            
            result = await generate_summary_llm(article_text, title, url, model)
            logger.info(f"Successfully generated summary for: {title}")
            
            duration_ms = (time.time() - start_time) * 1000
            logger.agent_complete("summary_agent", session_id, duration_ms)
            
            return result
            
    except Exception as e:
        logger.agent_error("summary_agent", session_id, str(e))
        return {
            "summary": f"Error: {str(e)}",
            "key_points": [],
            "intents": [],
            "values": [],
            "url": url,
            "title": title,
            "error": str(e)
        }

