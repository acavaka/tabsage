# TabSage Deployment Architecture

## Recommended Deployment Strategy

For the capstone project, we recommend a **hybrid approach** that maximizes points:

1. **Telegram Bot** → Cloud Run (must be always available)
2. **Web Interface** → Cloud Run (must be always available)
3. **Agents** → Vertex AI Agent Engine (for bonus points + proper architecture)
4. **Knowledge Graph** → Firestore (managed service, always available)

## Why This Architecture?

### Telegram Bot Requirements

**Telegram Bot MUST run on Cloud Run or similar web service** because:

1. **Webhook/Polling**: Telegram bot needs to:
   - Listen for incoming messages (polling or webhook)
   - Be accessible 24/7
   - Handle HTTP requests from Telegram servers

2. **Long-running process**: Bot must stay alive to receive messages

3. **Cannot run on Agent Engine**: Agent Engine is for agent execution, not web services

### Knowledge Graph (Firestore)

**Firestore is a managed service** - it's always available regardless of deployment:
- No deployment needed
- Automatically scales
- Accessible from anywhere with credentials
- Works with both Cloud Run and Agent Engine

### Agents on Agent Engine

**Why Agent Engine for agents:**
- ✅ **Bonus points**: "Agent Deployment" requires Agent Engine or similar
- ✅ **Proper architecture**: Agents are designed for Agent Engine
- ✅ **A2A Protocol**: Agent Engine supports A2A natively
- ✅ **Managed scaling**: Automatic scaling and management
- ✅ **Integration**: Works seamlessly with Vertex AI services

## Complete Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Telegram API ──→ Cloud Run (Telegram Bot)                   │
│                    │                                          │
│                    ├─→ Calls agents via A2A                  │
│                    └─→ Reads/writes to Firestore              │
│                                                               │
│  Browser ─────────→ Cloud Run (Web Interface)                 │
│                    │                                          │
│                    ├─→ Reads from Firestore                   │
│                    └─→ Visualizes knowledge graph             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ A2A Protocol
                            │
┌─────────────────────────────────────────────────────────────┐
│              Vertex AI Agent Engine                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Ingest Agent     │  │ KG Builder     │  │ Summary      │ │
│  │                  │  │ Agent          │  │ Agent        │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Topic Discovery │  │ Scriptwriter    │  │ Audio        │ │
│  │ Agent           │  │ Agent           │  │ Producer     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Evaluator       │  │ Editor Agent    │                   │
│  │ Agent           │  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                               │
│  All agents registered in Vertex AI Agent Registry            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Read/Write
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Firestore                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  • Knowledge Graph (entities, relations)                      │
│  • Articles metadata                                          │
│  • Summaries                                                  │
│  • Shared Memory (optional)                                   │
│                                                               │
│  Accessible from:                                             │
│  - Cloud Run services (Telegram Bot, Web)                    │
│  - Agent Engine agents                                        │
│  - Any service with credentials                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### 1. User Sends Article URL via Telegram

```
User → Telegram → Cloud Run (Bot) → Agent Engine (Ingest Agent)
                                              ↓
                                    Agent Engine (KG Builder)
                                              ↓
                                    Agent Engine (Summary Agent)
                                              ↓
                                    Firestore (Save results)
                                              ↓
                                    Cloud Run (Bot) → User (Summary)
```

### 2. User Searches Knowledge Graph

```
User → Telegram → Cloud Run (Bot) → Firestore (Query)
                                              ↓
                                    Cloud Run (Bot) → User (Results)
```

### 3. User Views Graph via Web Interface

```
User → Browser → Cloud Run (Web) → Firestore (Read graph)
                                              ↓
                                    Cloud Run (Web) → Browser (Visualization)
```

## Deployment Steps

### Step 1: Deploy Agents to Agent Engine

```bash
# For each agent, deploy to Agent Engine
adk deploy \
  --agent-name kg-builder-agent \
  --project YOUR_PROJECT_ID \
  --location us-central1 \
  --entry-point agents.kg_builder_a2a_agent:create_kg_builder_a2a_agent
```

### Step 2: Register Agents

```bash
# Register all agents in Vertex AI Registry
python scripts/register_agents.py
```

This will:
- Register agents in Vertex AI Agent Registry
- Get Agent Engine URLs
- Update configuration

### Step 3: Deploy Telegram Bot to Cloud Run

```bash
# Deploy bot (must be on Cloud Run for webhook/polling)
gcloud run deploy tabsage-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5
```

**Why Cloud Run for bot:**
- Must be accessible 24/7 for Telegram webhooks/polling
- Needs to handle HTTP requests
- Long-running process

### Step 4: Deploy Web Interface to Cloud Run

```bash
# Deploy web interface
gcloud run deploy tabsage-web \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60
```

### Step 5: Configure Firestore

```bash
# Create Firestore database (if not exists)
gcloud firestore databases create \
  --location=us-central1 \
  --type=firestore-native
```

Firestore is a managed service - no deployment needed, just configuration.

## Communication Flow

### Agent Calls from Telegram Bot

```python
# In telegram_bot.py
from registry.integration import create_remote_agent_from_registry

# Get agent from registry (Agent Engine)
kg_builder = create_remote_agent_from_registry("kg_builder_agent")

# Use agent via A2A
result = await kg_builder.run(payload)
```

### Firestore Access

```python
# Both Cloud Run and Agent Engine can access Firestore
from tools.kg_client import get_kg_instance

kg = get_kg_instance()  # Uses Firestore
articles = kg.get_articles()
```

## Environment Variables

After deployment, update `.env` with Agent Engine URLs:

```bash
# Agent Engine URLs (from registry)
KG_BUILDER_A2A_URL=https://agent-engine-url/agents/kg-builder-agent
TOPIC_DISCOVERY_A2A_URL=https://agent-engine-url/agents/topic-discovery-agent
# ... etc
```

## Cost Comparison

### Agent Engine
- **Per agent**: ~$0.10-0.50/hour (depending on usage)
- **8 agents**: ~$0.80-4.00/hour
- **Monthly**: ~$600-3,000 (if running 24/7)

### Cloud Run
- **Telegram Bot**: ~$0.40 per million requests
- **Web Interface**: ~$0.40 per million requests
- **Monthly**: ~$10-50 (typical usage)

### Firestore
- **Free tier**: 50K reads/day, 20K writes/day
- **Paid**: $0.06 per 100K reads, $0.18 per 100K writes
- **Monthly**: ~$5-20 (typical usage)

**Total estimated**: $15-70/month (light usage) to $600-3,000/month (heavy usage with Agent Engine)

## Alternative: All on Cloud Run

If you want to save costs or Agent Engine is not available:

### Pros:
- ✅ Lower cost
- ✅ Simpler deployment
- ✅ All services in one place

### Cons:
- ❌ No bonus points for Agent Engine deployment
- ❌ Less optimal architecture
- ❌ Manual scaling

### How It Works:

```
Telegram Bot (Cloud Run) → Agents (Cloud Run) → Firestore
Web Interface (Cloud Run) → Firestore
```

Agents run as separate Cloud Run services, Telegram bot calls them via HTTP.

## Recommendation for Capstone

**Use Agent Engine for agents** because:
1. **Bonus points**: "Agent Deployment" specifically mentions Agent Engine
2. **Proper architecture**: Shows understanding of Vertex AI ecosystem
3. **A2A Protocol**: Demonstrates proper agent-to-agent communication
4. **Professional**: Shows production-ready deployment

**Use Cloud Run for**:
- Telegram Bot (required - must be web-accessible)
- Web Interface (required - must be web-accessible)

**Use Firestore for**:
- Knowledge Graph (managed service - always available)

This hybrid approach gives you:
- ✅ All functionality working
- ✅ Bonus points for Agent Engine
- ✅ Professional architecture
- ✅ Scalable and maintainable

