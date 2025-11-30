# Quick Deployment Guide

## Recommended Architecture

```
Telegram Bot (Cloud Run) ──→ Agents (Agent Engine) ──→ Firestore
Web Interface (Cloud Run) ──→ Firestore
```

## Why This Architecture?

1. **Telegram Bot MUST be on Cloud Run**:
   - Needs to listen for messages 24/7
   - Must handle HTTP requests from Telegram
   - Cannot run on Agent Engine (Agent Engine is for agents, not web services)

2. **Agents SHOULD be on Agent Engine**:
   - Required for bonus points ("Agent Deployment")
   - Proper architecture for ADK agents
   - Native A2A support

3. **Firestore is always available**:
   - Managed service
   - Accessible from both Cloud Run and Agent Engine
   - No deployment needed

## Quick Deploy Steps

### 1. Deploy Agents to Agent Engine

```bash
# Deploy each agent
adk deploy --agent-name kg-builder-agent \
  --project YOUR_PROJECT_ID \
  --location us-central1 \
  --entry-point agents.kg_builder_a2a_agent:create_kg_builder_a2a_agent

# Repeat for all agents:
# - topic-discovery-agent
# - scriptwriter-agent
# - guest-agent
# - audio-producer-agent
# - evaluator-agent
# - editor-agent
# - publisher-agent
```

### 2. Register Agents

```bash
python scripts/register_agents.py
```

This gets Agent Engine URLs and updates configuration.

### 3. Deploy Telegram Bot (Cloud Run)

```bash
gcloud run deploy tabsage-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300
```

**Why Cloud Run**: Bot must be accessible 24/7 for Telegram webhooks.

### 4. Deploy Web Interface (Cloud Run)

```bash
gcloud run deploy tabsage-web \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 512Mi
```

### 5. Configure Firestore

```bash
# Create database (if not exists)
gcloud firestore databases create \
  --location=us-central1 \
  --type=firestore-native
```

Firestore is ready - no deployment needed!

## How It Works

### Article Processing Flow

```
1. User sends URL via Telegram
   ↓
2. Telegram Bot (Cloud Run) receives message
   ↓
3. Bot calls Ingest Agent (Agent Engine) via A2A
   ↓
4. Ingest Agent calls KG Builder Agent (Agent Engine) via A2A
   ↓
5. KG Builder Agent saves to Firestore
   ↓
6. Bot reads from Firestore and sends summary to user
```

### Knowledge Graph Access

- **Telegram Bot** reads/writes to Firestore directly
- **Web Interface** reads from Firestore directly
- **Agents** read/write to Firestore directly

Firestore is accessible from anywhere with credentials!

## Environment Variables

After Agent Engine deployment, update `.env`:

```bash
# Get Agent Engine URLs from registry
KG_BUILDER_A2A_URL=https://agent-engine-url/agents/kg-builder-agent
# ... etc
```

## Verification

```bash
# Check Cloud Run services
gcloud run services list

# Check Agent Engine agents
# (via Vertex AI Console or API)

# Test Telegram bot
# Send message to bot

# Test web interface
curl https://tabsage-web-xxx.run.app
```

## Troubleshooting

**Bot not receiving messages:**
- Check Cloud Run service is running
- Verify TELEGRAM_BOT_TOKEN is set
- Check bot is polling/webhook configured

**Agents not accessible:**
- Verify Agent Engine deployment
- Check agent registration
- Verify A2A URLs in .env

**Firestore access issues:**
- Check credentials: `gcloud auth application-default login`
- Verify Firestore database exists
- Check IAM permissions

