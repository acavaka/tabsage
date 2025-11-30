"""
OpenTelemetry tracing for TabSage

Based on Day 4a: Agent Observability
"""

import os
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    # Mock classes for when OpenTelemetry is not installed
    class trace:
        @staticmethod
        def get_tracer(name):
            return None
    
    class TracerProvider:
        pass


# Global tracer provider
_tracer_provider: Optional[TracerProvider] = None
_tracer = None


def setup_tracing(
    service_name: str = "tabsage",
    enable_console: bool = True,
    enable_otlp: bool = False,
    otlp_endpoint: Optional[str] = None
) -> None:
    """Setup OpenTelemetry tracing
    
    Args:
        service_name: Service name for traces
        enable_console: Enable console exporter (for debugging)
        enable_otlp: Enable OTLP exporter (for production)
        otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
    """
    global _tracer_provider, _tracer
    
    if not HAS_OPENTELEMETRY:
        print("⚠️ OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk")
        return
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    
    _tracer_provider = TracerProvider(resource=resource)
    
    if enable_console:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    if enable_otlp and otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    trace.set_tracer_provider(_tracer_provider)
    
    # Get tracer
    _tracer = trace.get_tracer(service_name)
    
    print(f"✅ Tracing configured for {service_name}")


def get_tracer(name: Optional[str] = None) -> Optional[Any]:
    """Get OpenTelemetry tracer
    
    Args:
        name: Tracer name (optional)
        
    Returns:
        Tracer instance or None if OpenTelemetry not available
    """
    global _tracer
    
    if not HAS_OPENTELEMETRY:
        return None
    
    if _tracer is None:
        # Initialize with defaults if not already set up
        setup_tracing()
    
    if name:
        return trace.get_tracer(name)
    
    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: Optional[str] = None
):
    """Context manager for creating a trace span
    
    Usage:
        with trace_span("agent_execution", {"agent_name": "ingest"}):
            # Your code here
            pass
    
    Args:
        name: Span name
        attributes: Optional span attributes
        kind: Span kind ("server", "client", "internal", etc.)
    """
    tracer = get_tracer()
    
    if tracer is None:
        # No-op if tracing not available
        yield
        return
    
    span_kind = None
    if kind:
        span_kind_map = {
            "server": trace.SpanKind.SERVER,
            "client": trace.SpanKind.CLIENT,
            "internal": trace.SpanKind.INTERNAL,
            "producer": trace.SpanKind.PRODUCER,
            "consumer": trace.SpanKind.CONSUMER,
        }
        span_kind = span_kind_map.get(kind, trace.SpanKind.INTERNAL)
    
    with tracer.start_as_current_span(name, kind=span_kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def trace_agent_execution(agent_name: str, session_id: str):
    """Decorator for tracing agent execution
    
    Usage:
        @trace_agent_execution("ingest_agent", "session_123")
        async def run_once(payload):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with trace_span(
                f"agent.{agent_name}",
                attributes={
                    "agent.name": agent_name,
                    "session.id": session_id,
                    "agent.operation": func.__name__
                },
                kind="internal"
            ):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

