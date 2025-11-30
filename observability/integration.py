"""
Integration helpers for adding observability to agents

Provides decorators and utilities for easy integration
"""

import time
from functools import wraps
from typing import Callable, Any, Dict

from observability.logging import get_logger
from observability.tracing import trace_span, get_tracer
from observability.metrics import (
    track_agent_execution,
    track_llm_request,
    track_llm_tokens,
    track_tool_call
)


def observe_agent(agent_name: str):
    """Decorator to add full observability to an agent's run_once function
    
    Adds:
    - Structured logging
    - OpenTelemetry tracing
    - Prometheus metrics
    
    Usage:
        @observe_agent("ingest_agent")
        async def run_once(payload: Dict[str, Any]) -> Dict[str, Any]:
            ...
    """
    logger = get_logger(agent_name)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @track_agent_execution(agent_name)
        async def wrapper(payload: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            session_id = payload.get("session_id", "unknown")
            episode_id = payload.get("episode_id", "unknown")
            
            # Log agent start
            logger.agent_start(agent_name, session_id, payload)
            
            # Create trace span
            with trace_span(
                f"agent.{agent_name}",
                attributes={
                    "agent.name": agent_name,
                    "session.id": session_id,
                    "episode.id": episode_id,
                    "agent.operation": func.__name__
                },
                kind="internal"
            ) as span:
                start_time = time.time()
                
                try:
                    # Execute agent
                    result = await func(payload, *args, **kwargs)
                    
                    # Log success
                    duration_ms = (time.time() - start_time) * 1000
                    logger.agent_complete(agent_name, session_id, duration_ms)
                    
                    # Add span attributes
                    if span:
                        span.set_attribute("agent.duration_ms", duration_ms)
                        span.set_attribute("agent.status", "success")
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    logger.agent_error(agent_name, session_id, str(e))
                    
                    # Add span error
                    if span:
                        span.set_attribute("agent.status", "error")
                        span.set_attribute("agent.error", str(e))
                    
                    raise
        
        return wrapper
    return decorator


def observe_llm_call(agent_name: str, model: str):
    """Context manager for observing LLM calls
    
    Usage:
        with observe_llm_call("ingest_agent", "gemini-2.5-flash-lite"):
            # LLM call here
            response = model.generate(...)
    """
    logger = get_logger(agent_name)
    
    class LLMObserver:
        def __init__(self):
            self.start_time = None
            self.prompt_length = 0
            self.response_length = 0
            self.tokens_input = 0
            self.tokens_output = 0
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            
            # Log LLM request/response
            logger.llm_request(agent_name, model, self.prompt_length)
            logger.llm_response(agent_name, model, self.response_length)
            
            # Track metrics
            track_llm_request(agent_name, model)
            if self.tokens_input > 0:
                track_llm_tokens(agent_name, model, self.tokens_input, "input")
            if self.tokens_output > 0:
                track_llm_tokens(agent_name, model, self.tokens_output, "output")
            
            return False
    
    return LLMObserver()


def observe_tool_call(agent_name: str, tool_name: str):
    """Context manager for observing tool calls
    
    Usage:
        with observe_tool_call("ingest_agent", "chunk_text_tool") as observer:
            result = tool_function(...)
            observer.set_args({"text": "..."})
    """
    logger = get_logger(agent_name)
    
    class ToolObserver:
        def __init__(self):
            self.start_time = None
            self.args = {}
            self.success = True
        
        def set_args(self, args: Dict[str, Any]):
            """Set tool arguments for logging"""
            self.args = args
        
        def __enter__(self):
            self.start_time = time.time()
            logger.tool_call(agent_name, tool_name, self.args)
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            self.success = exc_type is None
            
            # Log tool result
            logger.tool_result(agent_name, tool_name, self.success, duration * 1000)
            
            # Track metrics
            track_tool_call(agent_name, tool_name, duration, self.success)
            
            return False
    
    return ToolObserver()

