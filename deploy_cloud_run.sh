#!/bin/bash
# TabSage Cloud Run Deployment Script
# Deploys Telegram Bot, Web Interface, and Agents to Cloud Run

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please create .env file from .env.example"
    exit 1
fi

echo "=========================================="
echo "Deploying TabSage to Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="
echo ""

# Deploy Telegram Bot
echo "1. Deploying Telegram Bot..."
# Copy Dockerfile.bot to Dockerfile for deployment
cp Dockerfile.bot Dockerfile
gcloud run deploy tabsage-bot \
    --source . \
    --platform managed \
    --region $REGION \
    --env-vars-file .env \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 5 \
    --allow-unauthenticated \
    --quiet
rm -f Dockerfile

BOT_URL=$(gcloud run services describe tabsage-bot --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
echo "✅ Telegram Bot deployed: $BOT_URL"
echo ""

# Deploy Web Interface
echo "2. Deploying Web Interface..."
# Copy Dockerfile.web to Dockerfile for deployment
cp Dockerfile.web Dockerfile
gcloud run deploy tabsage-web \
    --source . \
    --platform managed \
    --region $REGION \
    --env-vars-file .env \
    --memory 512Mi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 3 \
    --allow-unauthenticated \
    --quiet
rm -f Dockerfile

WEB_URL=$(gcloud run services describe tabsage-web --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
echo "✅ Web Interface deployed: $WEB_URL"
echo ""

# Deploy Agents (optional - if not using Agent Engine)
echo "3. Deploying Agents to Cloud Run..."
echo "   (Skip if using Agent Engine)"
echo ""

AGENTS=(
    "kg-builder-agent:services/a2a/kg_builder_server.py:8002"
    "topic-discovery-agent:services/a2a/topic_discovery_server.py:8003"
    "scriptwriter-agent:services/a2a/scriptwriter_server.py:8004"
    "guest-agent:services/a2a/guest_server.py:8005"
    "audio-producer-agent:services/a2a/audio_producer_server.py:8006"
    "evaluator-agent:services/a2a/evaluator_server.py:8007"
    "editor-agent:services/a2a/editor_server.py:8008"
    "publisher-agent:services/a2a/publisher_server.py:8009"
)

for agent_config in "${AGENTS[@]}"; do
    IFS=':' read -r agent_name server_file default_port <<< "$agent_config"
    echo "   Deploying $agent_name..."
    
    # Create temporary entrypoint script
    cat > /tmp/run_agent.py << EOF
import os
import sys
sys.path.insert(0, '/app')
exec(open('$server_file').read())
EOF
    
    gcloud run deploy $agent_name \
        --source . \
        --platform managed \
        --region $REGION \
        --env-vars-file .env \
        --update-env-vars AGENT_SERVER=$server_file \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --allow-unauthenticated \
        --quiet || echo "   ⚠️  Failed to deploy $agent_name"
    
    AGENT_URL=$(gcloud run services describe $agent_name --region $REGION --format 'value(status.url)' 2>/dev/null || echo "")
    if [ ! -z "$AGENT_URL" ]; then
        echo "   ✅ $agent_name: $AGENT_URL"
    fi
done

echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo ""
echo "Services deployed:"
echo "  • Telegram Bot: $BOT_URL"
echo "  • Web Interface: $WEB_URL"
echo ""
echo "Next steps:"
echo "  1. Update .env with service URLs (if needed)"
echo "  2. Test Telegram bot: Send message to bot"
echo "  3. Test web interface: Open $WEB_URL"
echo "  4. Check logs: gcloud run services logs read SERVICE_NAME"
echo ""
echo "=========================================="

