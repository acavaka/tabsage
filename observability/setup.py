"""
Setup observability for TabSage

Initializes logging, tracing, and metrics based on configuration
"""

import logging
import os
from typing import Optional

from observability.logging import setup_logging, get_logger
from observability.tracing import setup_tracing
from observability.metrics import setup_metrics


def initialize_observability(
    enable_logging: bool = True,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    metrics_port: int = 8000,
    otlp_endpoint: Optional[str] = None
) -> None:
    """Initialize all observability components
    
    Args:
        enable_logging: Enable structured JSON logging
        enable_tracing: Enable OpenTelemetry tracing
        enable_metrics: Enable Prometheus metrics
        log_level: Logging level
        log_file: Optional log file path
        metrics_port: Port for Prometheus metrics server
        otlp_endpoint: OTLP endpoint for traces (e.g., "http://localhost:4317")
    """
    logger = logging.getLogger(__name__)
    
    # Setup logging
    if enable_logging:
        setup_logging(
            level=log_level,
            enable_json=True,
            log_file=log_file
        )
        logger.info("Structured logging initialized")
    
    if enable_tracing:
        setup_tracing(
            service_name="tabsage",
            enable_console=True,
            enable_otlp=otlp_endpoint is not None,
            otlp_endpoint=otlp_endpoint
        )
        logger.info("OpenTelemetry tracing initialized")
    
    if enable_metrics:
        setup_metrics(port=metrics_port, enable=True)
        logger.info("Prometheus metrics initialized")
    
    logger.info("Observability setup complete", extra={
        "event_type": "observability_init",
        "logging": enable_logging,
        "tracing": enable_tracing,
        "metrics": enable_metrics
    })


def initialize_from_env() -> None:
    """Initialize observability from environment variables
    
    Environment variables:
        - ENABLE_OBSERVABILITY: Enable all observability (default: true)
        - ENABLE_LOGGING: Enable logging (default: true)
        - ENABLE_TRACING: Enable tracing (default: true)
        - ENABLE_METRICS: Enable metrics (default: true)
        - LOG_LEVEL: Logging level (default: INFO)
        - LOG_FILE: Log file path (optional)
        - METRICS_PORT: Prometheus metrics port (default: 8000)
        - OTLP_ENDPOINT: OTLP endpoint for traces (optional)
    """
    enable_observability = os.getenv("ENABLE_OBSERVABILITY", "true").lower() == "true"
    
    if not enable_observability:
        return
    
    enable_logging = os.getenv("ENABLE_LOGGING", "true").lower() == "true"
    enable_tracing = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    log_file = os.getenv("LOG_FILE")
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")
    
    initialize_observability(
        enable_logging=enable_logging,
        enable_tracing=enable_tracing,
        enable_metrics=enable_metrics,
        log_level=log_level,
        log_file=log_file,
        metrics_port=metrics_port,
        otlp_endpoint=otlp_endpoint
    )

