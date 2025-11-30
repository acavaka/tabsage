# Cloud Run Deployment Guide

## What You Need for Cloud Run Deployment

### 1. Required Files

✅ **Already Created:**
- `Dockerfile.bot` - for Telegram Bot
- `Dockerfile.web` - for Web Interface  
- `Dockerfile.agent` - template for agents
- `.dockerignore` - excludes unnecessary files
- `pyproject.toml` - dependencies (includes uvicorn, gunicorn)
- `.env` - environment variables

### 2. Cloud Run Requirements

**For Telegram Bot:**
- Must listen on `0.0.0.0` (not `localhost`)
- Must use `PORT` environment variable (Cloud Run sets this)
- Must be always running (for polling/webhooks)

**For Web Interface:**
- Must listen on `0.0.0.0`
- Must use `PORT` environment variable
- Should use gunicorn for production

**For Agents:**
- Must listen on `0.0.0.0`
- Must use `PORT` environment variable
- Use uvicorn for ASGI apps

### 3. Environment Variables

All services need these in `.env`:
```bash
GOOGLE_API_KEY=...
GOOGLE_CLOUD_PROJECT=...
VERTEX_AI_LOCATION=...
KG_PROVIDER=firestore
TELEGRAM_BOT_TOKEN=...
```

### 4. Google Cloud Setup

```bash
# 1. Authenticate
gcloud auth login
gcloud auth application-default login

# 2. Set project
gcloud config set project YOUR_PROJECT_ID

# 3. Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable aiplatform.googleapis.com

# 4. Create Firestore database (if not already created)
# ✅ Firestore is already created - skip this step
# gcloud firestore databases create \
#   --location=us-central1 \
#   --type=firestore-native
```

## Deployment Steps

### Step 1: Deploy Telegram Bot

```bash
gcloud run deploy tabsage-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5 \
  --allow-unauthenticated
```

**Why `--source .`:**
- Cloud Run automatically builds Docker image
- Uses `Dockerfile.bot` if found, or creates one
- Installs dependencies from `pyproject.toml`

### Step 2: Deploy Web Interface

```bash
gcloud run deploy tabsage-web \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 3 \
  --allow-unauthenticated
```

### Step 3: Deploy Agents (if using Cloud Run instead of Agent Engine)

For each agent:

```bash
# Example: KG Builder Agent
gcloud run deploy kg-builder-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars-file .env \
  --set-env-vars AGENT_SERVER=services/a2a/kg_builder_server.py \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --allow-unauthenticated
```

**Note:** You'll need to create a custom Dockerfile or entrypoint script for agents.

## Simplified Deployment Script

Create `deploy_cloud_run.sh`:

```bash
#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "Deploying TabSage to Cloud Run..."

# Deploy Telegram Bot
echo "Deploying Telegram Bot..."
gcloud run deploy tabsage-bot \
  --source . \
  --platform managed \
  --region $REGION \
  --set-env-vars-file .env \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5 \
  --allow-unauthenticated

# Deploy Web Interface
echo "Deploying Web Interface..."
gcloud run deploy tabsage-web \
  --source . \
  --platform managed \
  --region $REGION \
  --set-env-vars-file .env \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 3 \
  --allow-unauthenticated

echo "✅ Deployment complete!"
echo ""
echo "Get service URLs:"
echo "  gcloud run services list"
```

## How It Works After Deployment

### Telegram Bot Flow

```
User → Telegram → Cloud Run (tabsage-bot) 
                    ↓
              Calls agents (via A2A or direct)
                    ↓
              Firestore (read/write)
                    ↓
              Cloud Run (tabsage-bot) → User
```

### Web Interface Flow

```
User → Browser → Cloud Run (tabsage-web)
                    ↓
              Firestore (read graph)
                    ↓
              Cloud Run (tabsage-web) → Browser
```

### Knowledge Graph

- **Firestore is always available** - no deployment needed
- Accessible from both Cloud Run services
- Just need credentials configured

## Verification

```bash
# List all services
gcloud run services list

# Get service URL
gcloud run services describe tabsage-bot --region us-central1 --format 'value(status.url)'

# Test endpoint
curl https://tabsage-bot-xxx.run.app/health
```

## Troubleshooting

### Bot not receiving messages
- Check service is running: `gcloud run services describe tabsage-bot`
- Check logs: `gcloud run services logs read tabsage-bot`
- Verify TELEGRAM_BOT_TOKEN is set

### Firestore access issues
- Check credentials: `gcloud auth application-default login`
- Verify Firestore database exists
- Check IAM permissions

### Port binding errors
- Ensure code uses `PORT` env var
- Ensure listening on `0.0.0.0` not `localhost`

## Cost Estimation

- **Telegram Bot**: ~$0.40 per million requests
- **Web Interface**: ~$0.40 per million requests  
- **Agents** (if on Cloud Run): ~$0.40 per million requests each
- **Firestore**: Free tier or ~$5-20/month

**Total**: ~$10-50/month (light usage)

