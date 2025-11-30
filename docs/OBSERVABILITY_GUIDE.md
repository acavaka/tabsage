# 🔎 Observability Guide for TabSage

> Complete observability setup based on Day 4a course

## Components

1. **Structured JSON logs** - for event analysis
2. **OpenTelemetry traces** - for workflow understanding
3. **Prometheus metrics** - for performance monitoring
4. **ADK Web UI** - for visualization and debugging

---

## Quick Start

### 1. Install Dependencies

```bash
pip install pythonjsonlogger prometheus-client \
    opentelemetry-api opentelemetry-sdk \
    opentelemetry-exporter-otlp-proto-grpc
```

### 2. Run with Observability

```bash
# Run Telegram bot with observability
python3 run_with_observability.py
```

### 3. Access Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics
```

### 4. Launch ADK Web UI

```bash
# In separate terminal
adk web --app-name tabsage
```

Open browser: http://localhost:8000 (or URL from command output)

---

## Structured Logs

### Format

Logs are output in JSON format:

```json
{
  "timestamp": "2025-11-29T02:00:00.000Z",
  "level": "INFO",
  "name": "tabsage.agents.ingest_agent",
  "message": "Agent ingest_agent started",
  "event_type": "agent_start",
  "agent_name": "ingest_agent",
  "session_id": "session_123",
  "payload_keys": ["raw_text", "metadata"]
}
```

### Event Types

- `agent_start` - agent started execution
- `agent_complete` - agent completed execution
- `agent_error` - error in agent
- `llm_request` - request to LLM
- `llm_response` - response from LLM
- `tool_call` - tool call
- `tool_result` - tool result

### Configuration

```python
from tabsage.observability.logging import setup_logging

# Configure logging
setup_logging(
    level=logging.INFO,
    enable_json=True,
    log_file="tabsage.log"
)
```

---

## OpenTelemetry Traces

### What is Tracked

- Agent execution
- LLM requests
- Tool calls
- Errors and exceptions

### Configuration

```python
from tabsage.observability.tracing import setup_tracing

# Configure tracing
setup_tracing(
    service_name="tabsage",
    enable_console=True,  # For debugging
    enable_otlp=True,     # For production
    otlp_endpoint="http://localhost:4317"
)
```

### Usage in Code

```python
from tabsage.observability.tracing import trace_span

with trace_span("my_operation", {"key": "value"}):
    # Your code
    result = do_something()
```

---

## Prometheus Metrics

### Available Metrics

#### Agents
- `tabsage_agent_requests_total` - total number of requests
- `tabsage_agent_duration_seconds` - execution time
- `tabsage_agent_errors_total` - number of errors

#### LLM
- `tabsage_llm_requests_total` - requests to LLM
- `tabsage_llm_tokens_total` - token usage
- `tabsage_llm_duration_seconds` - LLM response time

#### Tools
- `tabsage_tool_calls_total` - tool calls
- `tabsage_tool_duration_seconds` - execution time

#### Knowledge Graph
- `tabsage_kg_entities_total` - added entities
- `tabsage_kg_relations_total` - added relations

### Query Metrics

```bash
# All metrics
curl http://localhost:8000/metrics

# Specific metric
curl http://localhost:8000/metrics | grep tabsage_agent_requests_total
```

### Grafana Dashboard

You can create a Grafana dashboard to visualize metrics.

---

## ADK Web UI

### Launch

```bash
# Launch web UI
adk web --app-name tabsage

# With port specification
adk web --app-name tabsage --port 8001
```

### Features

- View agent sessions
- Message history
- Execution tracing
- Error debugging

### Requirements

- All agents must use the same `app_name`
- Sessions must be properly configured

---

## Integration in Agents

### Automatic Integration

Use the `@observe_agent` decorator:

```python
from tabsage.observability.integration import observe_agent

@observe_agent("ingest_agent")
async def run_once(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Your agent code
    ...
```

This automatically adds:
- Start/complete logging
- Execution tracing
- Performance metrics

### Manual Integration

```python
from tabsage.observability.logging import get_logger
from tabsage.observability.tracing import trace_span
from tabsage.observability.metrics import track_agent_execution

logger = get_logger(__name__)

@track_agent_execution("my_agent")
async def run_once(payload):
    with trace_span("my_agent.run_once"):
        logger.agent_start("my_agent", payload["session_id"], payload)
        # Your code
        logger.agent_complete("my_agent", payload["session_id"], duration_ms)
```

---

## 🌍 Environment Variables

```bash
# Enable/disable observability
export ENABLE_OBSERVABILITY=true

# Components
export ENABLE_LOGGING=true
export ENABLE_TRACING=true
export ENABLE_METRICS=true

# Settings
export LOG_LEVEL=INFO
export LOG_FILE=tabsage.log
export METRICS_PORT=8000
export OTLP_ENDPOINT=http://localhost:4317
```

---

## Usage Examples

### View Logs in Real Time

```bash
# JSON logs
python3 run_with_observability.py | jq '.'

# Filter by event type
python3 run_with_observability.py | jq 'select(.event_type == "agent_start")'
```

### Monitor Metrics

```bash
# Query metrics every 5 seconds
watch -n 5 'curl -s http://localhost:8000/metrics | grep tabsage_agent'
```

### Debug with ADK Web UI

1. Run `adk web --app-name tabsage`
2. Open UI in browser
3. Execute request to agent
4. View trace in UI

---

## 🐛 Troubleshooting

### Metrics Not Displaying

```bash
# Check that server is running
curl http://localhost:8000/metrics

# Check port
netstat -an | grep 8000
```

### Traces Not Working

```bash
# Make sure OpenTelemetry is installed
pip list | grep opentelemetry

# Check console export
# Traces should be output to console
```

### ADK Web UI Not Starting

```bash
# Check app_name
# All agents must use the same app_name

# Check sessions
# Sessions must be properly configured
```

---

## 📚 Additional Resources

- [ADK Documentation](https://google.github.io/adk-docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)

---

**Last updated:** 2025-11-29

