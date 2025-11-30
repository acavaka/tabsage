# TabSage Deployment Guide

## Overview

This guide covers deploying TabSage to Google Cloud Platform, specifically:
- Deploying agents to Vertex AI Agent Engine
- Deploying services to Cloud Run
- Setting up environment variables
- Registering agents in Vertex AI Agent Registry

## Prerequisites

1. **Google Cloud Project**
   - Active GCP project with billing enabled
   - Vertex AI API enabled
   - Cloud Run API enabled
   - Firestore API enabled

2. **Authentication**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Environment Variables**
   - Create `.env` file from `.env.example`
   - Set all required variables (see Configuration section)

4. **Dependencies**
   ```bash
   pip install -e .
   ```

## Configuration

### Environment Variables

Create `.env` file with the following variables:

```bash
# Google API Configuration
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash-lite

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1

# Knowledge Graph Provider
KG_PROVIDER=firestore

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHANNEL_ID=your-telegram-channel-id

# A2A Agent URLs (will be set after deployment)
KG_BUILDER_A2A_URL=https://kg-builder-agent-xxx.run.app
TOPIC_DISCOVERY_A2A_URL=https://topic-discovery-agent-xxx.run.app
SCRIPTWRITER_A2A_URL=https://scriptwriter-agent-xxx.run.app
GUEST_A2A_URL=https://guest-agent-xxx.run.app
AUDIO_PRODUCER_A2A_URL=https://audio-producer-agent-xxx.run.app
EVALUATOR_A2A_URL=https://evaluator-agent-xxx.run.app
EDITOR_A2A_URL=https://editor-agent-xxx.run.app
PUBLISHER_A2A_URL=https://publisher-agent-xxx.run.app
```

## Deployment Architecture

**Recommended: Hybrid Approach**

- **Telegram Bot** → Cloud Run (must be web-accessible 24/7)
- **Web Interface** → Cloud Run (must be web-accessible)
- **Agents** → Vertex AI Agent Engine (for bonus points + proper architecture)
- **Knowledge Graph** → Firestore (managed service, always available)

For detailed architecture explanation, see [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md).

## Deployment Options

### Option 1: Vertex AI Agent Engine (Recommended for Agents)

Vertex AI Agent Engine provides managed deployment for ADK agents.

**Why Agent Engine for agents:**
- ✅ Bonus points for "Agent Deployment"
- ✅ Proper architecture for ADK agents
- ✅ Native A2A protocol support
- ✅ Automatic scaling and management

#### Step 1: Prepare Agent Code

Each agent needs to be packaged for deployment. Create a deployment package:

```bash
# Create deployment directory
mkdir -p deploy/agents
cp -r agents deploy/
cp -r core deploy/
cp -r tools deploy/
cp -r schemas deploy/
cp -r observability deploy/
cp pyproject.toml deploy/
```

#### Step 2: Deploy Individual Agents

For each agent, create a deployment script. Example for KG Builder Agent:

```bash
# deploy/kg_builder_agent_deploy.sh
#!/bin/bash

PROJECT_ID=$(gcloud config get-value project)
LOCATION="us-central1"
AGENT_NAME="kg-builder-agent"

# Deploy using ADK CLI
adk deploy \
  --agent-name $AGENT_NAME \
  --project $PROJECT_ID \
  --location $LOCATION \
  --entry-point agents.kg_builder_a2a_agent:create_kg_builder_a2a_agent \
  --env-vars GOOGLE_API_KEY,GOOGLE_CLOUD_PROJECT,VERTEX_AI_LOCATION
```

#### Step 3: Register Agents

After deployment, register agents in Vertex AI Agent Registry:

```bash
python scripts/register_agents.py
```

This script will:
- Register all agents in the registry
- Set agent URLs to Cloud Run endpoints
- Configure agent metadata

### Option 2: Cloud Run Deployment (For Telegram Bot & Web)

**Telegram Bot and Web Interface MUST be on Cloud Run** because they need to:
- Be accessible 24/7 for webhooks/polling
- Handle HTTP requests
- Stay running continuously

### Option 3: Cloud Run for Agents (Alternative)

If Agent Engine is not available, agents can also run on Cloud Run (but you lose bonus points).

#### Step 1: Create Dockerfile

Create `Dockerfile` for each agent service:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Run agent server
CMD ["python", "services/a2a/kg_builder_server.py"]
```

#### Step 2: Build and Deploy

```bash
# Set variables
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="kg-builder-agent"
REGION="us-central1"

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10
```

#### Step 3: Update Environment Variables

After deployment, update `.env` with Cloud Run URLs:

```bash
# Get service URLs
KG_BUILDER_A2A_URL=$(gcloud run services describe kg-builder-agent --region us-central1 --format 'value(status.url)')
# ... repeat for all agents
```

### Option 3: Deploy Main Services

#### Telegram Bot

```bash
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

#### Web Interface

```bash
gcloud run deploy tabsage-web \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 3
```

## Post-Deployment

### 1. Verify Deployment

```bash
# Check Cloud Run services
gcloud run services list

# Test agent endpoint
curl https://kg-builder-agent-xxx.run.app/health
```

### 2. Register Agents

```bash
# Register all agents in Vertex AI Registry
python scripts/register_agents.py
```

### 3. Configure Firestore

```bash
# Create Firestore database (if not exists)
gcloud firestore databases create \
  --location=us-central1 \
  --type=firestore-native
```

### 4. Set Up Monitoring

- Enable Cloud Monitoring
- Set up alerts for agent errors
- Monitor Cloud Run metrics

## Deployment Script

Create `deploy.sh` script for automated deployment:

```bash
#!/bin/bash

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "Deploying TabSage to $PROJECT_ID..."

# Deploy agents
echo "Deploying agents..."
for agent in kg-builder topic-discovery scriptwriter guest audio-producer evaluator editor publisher; do
  echo "Deploying $agent..."
  gcloud run deploy $agent-agent \
    --source . \
    --platform managed \
    --region $REGION \
    --set-env-vars-file .env \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300
done

# Deploy main services
echo "Deploying main services..."
gcloud run deploy tabsage-bot --source . --platform managed --region $REGION --set-env-vars-file .env
gcloud run deploy tabsage-web --source . --platform managed --region $REGION --set-env-vars-file .env

# Register agents
echo "Registering agents..."
python scripts/register_agents.py

echo "Deployment complete!"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth application-default login
   ```

2. **Permission Errors**
   ```bash
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="user:YOUR_EMAIL" \
     --role="roles/aiplatform.user"
   ```

3. **Environment Variables Not Set**
   - Check `.env` file exists
   - Verify variables are set in Cloud Run
   - Use `gcloud run services describe SERVICE_NAME` to check

4. **Agent Registration Fails**
   - Verify Vertex AI API is enabled
   - Check project permissions
   - Ensure agents are deployed first

## Cost Estimation

- **Cloud Run**: ~$0.40 per million requests
- **Vertex AI**: Pay per API call
- **Firestore**: Free tier: 50K reads/day, 20K writes/day
- **Storage**: Minimal for agent code

Estimated monthly cost for moderate usage: $10-50

## Security Best Practices

1. **Secrets Management**
   - Use Secret Manager for sensitive data
   - Never commit `.env` file
   - Rotate API keys regularly

2. **IAM Roles**
   - Use least privilege principle
   - Create service accounts for agents
   - Limit public access

3. **Network Security**
   - Use VPC for internal communication
   - Enable Cloud Armor for DDoS protection
   - Use HTTPS only

## Next Steps

After deployment:
1. Test all agent endpoints
2. Monitor logs and metrics
3. Set up alerts
4. Update documentation with production URLs
5. Create demo video

## References

- [Google ADK Deployment Guide](https://github.com/google/adk-python)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/docs/agent-builder)

