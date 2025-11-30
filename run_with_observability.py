#!/usr/bin/env python3
"""
Run TabSage with full observability enabled

This script initializes observability (logging, tracing, metrics) and
provides access to ADK web UI.
"""

import os
import asyncio

from observability.setup import initialize_observability
from services.bot.telegram_bot import main as bot_main

# Initialize observability
initialize_observability(
    enable_logging=True,
    enable_tracing=True,
    enable_metrics=True,
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    metrics_port=int(os.getenv("METRICS_PORT", "8000"))
)

print("=" * 60)
print("TabSage with Observability")
print("=" * 60)
print()
print("Observability enabled:")
print("   - Structured JSON logging")
print("   - OpenTelemetry tracing")
print("   - Prometheus metrics on port 8000")
print()
print("Access points:")
print("   - Prometheus metrics: http://localhost:8000/metrics")
print("   - ADK Web UI: Run 'adk web --app-name tabsage' in another terminal")
print()
print("=" * 60)
print()

if __name__ == "__main__":
    asyncio.run(bot_main())

