"""
Prometheus metrics for TabSage

Based on Day 4a: Agent Observability
"""

import time
from typing import Dict, Any, Optional
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    # Mock classes for when Prometheus is not installed
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
    
    def start_http_server(*args, **kwargs):
        pass


# Global metrics
_metrics_initialized = False

# Agent metrics
agent_requests_total = Counter(
    'tabsage_agent_requests_total',
    'Total number of agent requests',
    ['agent_name', 'status']
)

agent_duration_seconds = Histogram(
    'tabsage_agent_duration_seconds',
    'Agent execution time in seconds',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

agent_errors_total = Counter(
    'tabsage_agent_errors_total',
    'Total number of agent errors',
    ['agent_name', 'error_type']
)

# LLM metrics
llm_requests_total = Counter(
    'tabsage_llm_requests_total',
    'Total number of LLM requests',
    ['agent_name', 'model']
)

llm_tokens_total = Counter(
    'tabsage_llm_tokens_total',
    'Total number of LLM tokens',
    ['agent_name', 'model', 'type']  # type: input, output
)

llm_duration_seconds = Histogram(
    'tabsage_llm_duration_seconds',
    'LLM request duration in seconds',
    ['agent_name', 'model']
)

# Tool metrics
tool_calls_total = Counter(
    'tabsage_tool_calls_total',
    'Total number of tool calls',
    ['agent_name', 'tool_name', 'status']
)

tool_duration_seconds = Histogram(
    'tabsage_tool_duration_seconds',
    'Tool execution time in seconds',
    ['agent_name', 'tool_name']
)

# Knowledge Graph metrics
kg_entities_total = Counter(
    'tabsage_kg_entities_total',
    'Total number of entities added to KG',
    ['entity_type']
)

kg_relations_total = Counter(
    'tabsage_kg_relations_total',
    'Total number of relations added to KG',
    ['relation_type']
)

# System metrics
active_sessions = Gauge(
    'tabsage_active_sessions',
    'Number of active sessions'
)

articles_processed_total = Counter(
    'tabsage_articles_processed_total',
    'Total number of articles processed',
    ['status']
)


def setup_metrics(port: int = 8000, enable: bool = True) -> None:
    """Setup Prometheus metrics server
    
    Args:
        port: Port for metrics HTTP server
        enable: Enable metrics collection
    """
    global _metrics_initialized
    
    if not HAS_PROMETHEUS:
        print("⚠️ Prometheus client not installed. Install with: pip install prometheus-client")
        return
    
    if not enable:
        return
    
    try:
        start_http_server(port)
        _metrics_initialized = True
        print(f"✅ Prometheus metrics server started on port {port}")
        print(f"   Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        print(f"⚠️ Failed to start metrics server: {e}")


def get_metrics() -> Dict[str, Any]:
    """Get current metrics values
    
    Returns:
        Dictionary with current metric values
    """
    if not HAS_PROMETHEUS:
        return {}
    
    # This would require accessing internal Prometheus registry
    # For now, return empty dict
    return {}


def track_agent_execution(agent_name: str):
    """Decorator to track agent execution metrics
    
    Usage:
        @track_agent_execution("ingest_agent")
        async def run_once(payload):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            error_type = None
            
            try:
                # Increment request counter
                agent_requests_total.labels(agent_name=agent_name, status="started").inc()
                
                result = await func(*args, **kwargs)
                
                if isinstance(result, dict) and "error" in result:
                    status = "error"
                    error_type = result.get("error_type", "unknown")
                    agent_errors_total.labels(agent_name=agent_name, error_type=error_type).inc()
                
                return result
                
            except Exception as e:
                status = "error"
                error_type = type(e).__name__
                agent_errors_total.labels(agent_name=agent_name, error_type=error_type).inc()
                raise
            
            finally:
                # Record duration
                duration = time.time() - start_time
                agent_duration_seconds.labels(agent_name=agent_name).observe(duration)
                
                # Record final status
                agent_requests_total.labels(agent_name=agent_name, status=status).inc()
        
        return wrapper
    return decorator


def track_llm_request(agent_name: str, model: str):
    """Track LLM request metrics
    
    Args:
        agent_name: Name of the agent making the request
        model: LLM model name
    """
    if not HAS_PROMETHEUS:
        return
    
    llm_requests_total.labels(agent_name=agent_name, model=model).inc()


def track_llm_tokens(agent_name: str, model: str, tokens: int, token_type: str = "input"):
    """Track LLM token usage
    
    Args:
        agent_name: Name of the agent
        model: LLM model name
        tokens: Number of tokens
        token_type: "input" or "output"
    """
    if not HAS_PROMETHEUS:
        return
    
    llm_tokens_total.labels(agent_name=agent_name, model=model, type=token_type).inc(tokens)


def track_tool_call(agent_name: str, tool_name: str, duration: float, success: bool = True):
    """Track tool call metrics
    
    Args:
        agent_name: Name of the agent
        tool_name: Name of the tool
        duration: Execution duration in seconds
        success: Whether the call was successful
    """
    if not HAS_PROMETHEUS:
        return
    
    status = "success" if success else "error"
    tool_calls_total.labels(agent_name=agent_name, tool_name=tool_name, status=status).inc()
    tool_duration_seconds.labels(agent_name=agent_name, tool_name=tool_name).observe(duration)


def track_kg_entity(entity_type: str):
    """Track knowledge graph entity addition
    
    Args:
        entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
    """
    if not HAS_PROMETHEUS:
        return
    
    kg_entities_total.labels(entity_type=entity_type).inc()


def track_kg_relation(relation_type: str):
    """Track knowledge graph relation addition
    
    Args:
        relation_type: Type of relation
    """
    if not HAS_PROMETHEUS:
        return
    
    kg_relations_total.labels(relation_type=relation_type).inc()

