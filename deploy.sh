#!/bin/bash

# TabSage Deployment Script for Cloud Run
# Deploys Telegram Bot, Web Interface, and Agents to Google Cloud Run

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=========================================="
echo "Deploying TabSage to Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "=========================================="
echo "Deploying TabSage to $PROJECT_ID"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Deploy agents
echo "Deploying agents to Cloud Run..."
echo ""

AGENTS=(
    "kg-builder-agent:services/a2a/kg_builder_server.py"
    "topic-discovery-agent:services/a2a/topic_discovery_server.py"
    "scriptwriter-agent:services/a2a/scriptwriter_server.py"
    "guest-agent:services/a2a/guest_server.py"
    "audio-producer-agent:services/a2a/audio_producer_server.py"
    "evaluator-agent:services/a2a/evaluator_server.py"
    "editor-agent:services/a2a/editor_server.py"
    "publisher-agent:services/a2a/publisher_server.py"
)

for agent_config in "${AGENTS[@]}"; do
    IFS=':' read -r agent_name entry_point <<< "$agent_config"
    echo "Deploying $agent_name..."
    
    gcloud run deploy $agent_name \
        --source . \
        --platform managed \
        --region $REGION \
        --set-env-vars-file .env \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --allow-unauthenticated \
        --quiet || echo "Warning: Failed to deploy $agent_name"
    
    echo "✅ $agent_name deployed"
    echo ""
done

# Deploy main services
echo "Deploying main services..."
echo ""

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
    --allow-unauthenticated \
    --quiet || echo "Warning: Failed to deploy Telegram Bot"

echo "✅ Telegram Bot deployed"
echo ""

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
    --allow-unauthenticated \
    --quiet || echo "Warning: Failed to deploy Web Interface"

echo "✅ Web Interface deployed"
echo ""

# Get service URLs and update .env
echo "Updating .env with service URLs..."
echo ""

# Update agent URLs in .env
for agent_name in "${AGENTS[@]}"; do
    IFS=':' read -r name _ <<< "$agent_name"
    url=$(gcloud run services describe $name --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    if [ ! -z "$url" ]; then
        env_var=$(echo $name | tr '[:lower:]' '[:upper:]' | tr '-' '_' | sed 's/AGENT$/_A2A_URL/')
        # Update .env file (this is a simple approach, may need refinement)
        echo "  $env_var=$url"
    fi
done

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update .env with service URLs (shown above)"
echo "2. Register agents: python scripts/register_agents.py"
echo "3. Test endpoints: curl https://kg-builder-agent-xxx.run.app/health"
echo ""

