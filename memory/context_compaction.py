"""
Context Compaction - context compression for optimization

Based on Day 3b: Memory Management
Compresses conversation context, preserving important information.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from observability.logging import get_logger

logger = get_logger(__name__)


def compact_context(
    events: List[Dict[str, Any]],
    max_tokens: int = 2000,
    preserve_recent: int = 5
) -> List[Dict[str, Any]]:
    """
    Compresses context, preserving important information.
    
    Args:
        events: List of events from session
        max_tokens: Maximum number of tokens (approximately)
        preserve_recent: Number of recent events to preserve
        
    Returns:
        Compressed list of events
    """
    if len(events) <= preserve_recent:
        return events
    
    # Preserve last N events
    recent_events = events[-preserve_recent:]
    
    # Compress old events
    old_events = events[:-preserve_recent]
    
    # Simple strategy: keep only important events
    # (tool calls, important responses)
    important_events = []
    
    for event in old_events:
        # Preserve tool calls
        if event.get("type") == "tool_call" or "tool" in str(event).lower():
            important_events.append(event)
        # Preserve final responses
        elif event.get("type") == "final_response":
            important_events.append(event)
        # Skip intermediate messages
    
    # Combine
    compacted = important_events + recent_events
    
    logger.info(f"Context compacted: {len(events)} -> {len(compacted)} events", extra={
        "event_type": "context_compaction",
        "original_count": len(events),
        "compacted_count": len(compacted),
        "reduction": len(events) - len(compacted)
    })
    
    return compacted


def summarize_context(
    events: List[Dict[str, Any]],
    model: Optional[Any] = None
) -> str:
    """
    Creates brief context summary using LLM.
    
    Args:
        events: List of events
        model: LLM model for summary generation (optional)
        
    Returns:
        Text summary of context
    """
    if not events:
        return ""
    
    # Simple summary without LLM (can be improved)
    summary_parts = []
    
    for event in events:
        if event.get("type") == "user_message":
            text = event.get("content", "")[:100]
            summary_parts.append(f"User: {text}...")
        elif event.get("type") == "tool_call":
            tool_name = event.get("tool_name", "unknown")
            summary_parts.append(f"Tool: {tool_name}")
        elif event.get("type") == "final_response":
            text = event.get("content", "")[:100]
            summary_parts.append(f"Response: {text}...")
    
    summary = "\n".join(summary_parts[:10])  # First 10 events
    
    logger.debug("Context summarized", extra={
        "event_type": "context_summarization",
        "events_count": len(events),
        "summary_length": len(summary)
    })
    
    return summary


def estimate_tokens(text: str) -> int:
    """
    Estimates token count in text (approximately).
    
    Args:
        text: Text to estimate
        
    Returns:
        Approximate token count
    """
    # Simple estimate: ~4 characters per token
    return len(text) // 4

