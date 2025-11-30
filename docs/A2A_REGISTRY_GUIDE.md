# 🔗 A2A Registry Guide for TabSage

> Centralized registry via Vertex AI Agent Builder

## Overview

**Vertex AI Agent Registry** - centralized system for managing A2A agents:
- Automatic registration on deployment
- Agent discovery by name
- Version management
- Agent metadata (URL, capabilities, version)

---

## Quick Start

### 1. Register All Agents

```bash
# Register all agents in registry
python3 scripts/register_agents.py
```

This will register all agents:
- `kg_builder_agent`
- `topic_discovery_agent`
- `scriptwriter_agent`
- `guest_agent`
- `audio_producer_agent`
- `evaluator_agent`
- `editor_agent`
- `publisher_agent`

### 2. Usage in Code

```python
from tabsage.registry.vertex_ai_registry import get_registry, discover_agent
from tabsage.registry.integration import create_remote_agent_from_registry

# Discover agent via registry
agent_info = discover_agent("kg_builder_agent")
if agent_info:
    print(f"Agent URL: {agent_info['url']}")

# Create RemoteA2aAgent via registry
remote_agent = create_remote_agent_from_registry(
    agent_name="kg_builder_agent",
    fallback_url="http://localhost:8002"  # Fallback if not found
)
```

---

## Architecture

### Local Development

```
┌─────────────────┐
│  Local Registry │  (in-memory)
│  (fallback)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agents         │
│  (localhost)    │
└─────────────────┘
```

### Production (Vertex AI)

```
┌──────────────────────┐
│  Vertex AI Agent     │
│  Builder Registry    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Agent Engine         │
│  (deployed agents)    │
└──────────────────────┘
```

---

## API

### VertexAIAgentRegistry

```python
from tabsage.registry.vertex_ai_registry import VertexAIAgentRegistry

# Initialization
registry = VertexAIAgentRegistry(
    project_id="YOUR_PROJECT_ID",
    location="us-central1"
)

# Register agent
result = registry.register_agent(
    agent_name="kg_builder_agent",
    agent_url="https://kg-builder-agent-xxx.run.app",
    agent_description="KG Builder Agent",
    version="1.0.0",
    capabilities=["entity_extraction", "relation_extraction"]
)

# Discover agent
agent_info = registry.discover_agent("kg_builder_agent")

# List all agents
all_agents = registry.list_agents()

# Filter by capability
kg_agents = registry.list_agents(filter_by_capability="knowledge_graph")
```

---

## 🔄 Orchestrator Integration

Orchestrator automatically uses registry for agent discovery:

```python
from tabsage.registry.integration import create_remote_agent_from_registry

# Instead of hardcoded URL
# old: RemoteA2aAgent(agent_card=f"{KG_BUILDER_A2A_URL}/.well-known/agent-card.json")

# New way via registry
kg_agent = create_remote_agent_from_registry(
    agent_name="kg_builder_agent",
    fallback_url=KG_BUILDER_A2A_URL  # Fallback for local development
)
```

---

## 🚢 Deployment to Vertex AI

### After Deployment via Agent Engine

After deploying agents via `adk deploy`, they are automatically registered in Vertex AI Agent Builder:

1. **Deploy agent:**
```bash
cd tabsage
adk deploy kg_builder_agent \
    --project-id YOUR_PROJECT_ID \
    --location us-central1
```

2. **Automatic registration:**
   - Agent Engine automatically registers agent in Agent Builder
   - Registry receives URL from Cloud Run
   - Metadata is saved in Vertex AI

3. **Discovery:**
```python
# Registry will automatically find deployed agent
agent_info = discover_agent("kg_builder_agent")
# Returns Cloud Run URL instead of localhost
```

---

## Configuration

### Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export VERTEX_AI_LOCATION="us-central1"
```

### In Code

```python
from tabsage.config import GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION

registry = VertexAIAgentRegistry(
    project_id=GOOGLE_CLOUD_PROJECT,
    location=VERTEX_AI_LOCATION
)
```

---

## Agent Capabilities

Each agent is registered with capabilities:

| Agent | Capabilities |
|-------|-------------|
| kg_builder_agent | `entity_extraction`, `relation_extraction`, `knowledge_graph` |
| topic_discovery_agent | `topic_discovery`, `content_analysis` |
| scriptwriter_agent | `script_generation`, `content_creation` |
| guest_agent | `persona_simulation`, `expert_qa` |
| audio_producer_agent | `tts`, `audio_production` |
| evaluator_agent | `quality_evaluation`, `text_evaluation`, `audio_evaluation` |
| editor_agent | `human_review`, `content_editing` |
| publisher_agent | `publishing`, `distribution` |

---

## Agent Search

### By Name

```python
agent_info = discover_agent("kg_builder_agent")
```

### By Capability

```python
# Find all agents with knowledge_graph capability
kg_agents = registry.list_agents(filter_by_capability="knowledge_graph")
```

### All Agents

```python
all_agents = registry.list_agents()
for agent in all_agents:
    print(f"{agent['name']}: {agent['url']}")
```

---

## 🐛 Troubleshooting

### Agent Not Found in Registry

```python
# Use fallback URL
agent = create_remote_agent_from_registry(
    agent_name="kg_builder_agent",
    fallback_url="http://localhost:8002"  # Local development
)
```

### Vertex AI Unavailable

Registry automatically uses in-memory fallback if Vertex AI is unavailable.

### Check Registration

```bash
# Run registration script
python3 scripts/register_agents.py

# Check in code
from tabsage.registry.vertex_ai_registry import get_registry
registry = get_registry()
agents = registry.list_agents()
print(f"Registered agents: {len(agents)}")
```

---

## 📚 Additional Resources

- [Vertex AI Agent Builder](https://cloud.google.com/agent-builder)
- [Agent Engine Documentation](https://docs.cloud.google.com/agent-builder/agent-engine/overview)
- [Day 5a Notebook](../Practice/day-5a-agent2agent-communication.ipynb)
- [Day 5b Notebook](../Practice/day-5b-agent-deployment.ipynb)

---

**Last updated:** 2025-11-29

