"""Configuration for TabSage agents"""

import os
import logging
from typing import Dict, Any
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Initialize observability if enabled
try:
    from observability.setup import initialize_from_env
    initialize_from_env()
except ImportError:
    # Observability not available, use basic logging
    logging.basicConfig(level=logging.INFO)

# Gemini API configuration
# Must be set via environment variable GOOGLE_API_KEY
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY environment variable is required. "
        "Please set it in .env file or export it in your environment."
    )
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# Set key in environment if it wasn't set (needed for Gemini API)
if not os.getenv("GOOGLE_API_KEY") and GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# Google Cloud Configuration
# Must be set via environment variables
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
if not GOOGLE_CLOUD_PROJECT:
    raise ValueError(
        "GOOGLE_CLOUD_PROJECT environment variable is required. "
        "Please set it in .env file or export it in your environment."
    )
VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")

# Knowledge Graph Provider
KG_PROVIDER = os.getenv("KG_PROVIDER", "inmemory")  # inmemory, firestore, neo4j, neptune, pgvector

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN environment variable is required. "
        "Please set it in .env file or export it in your environment."
    )
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # Optional: Channel ID for publishing (e.g., @your_channel or -1001234567890)

# A2A Configuration - URLs for all agents
KG_BUILDER_A2A_URL = os.getenv("KG_BUILDER_A2A_URL", "http://localhost:8002")
TOPIC_DISCOVERY_A2A_URL = os.getenv("TOPIC_DISCOVERY_A2A_URL", "http://localhost:8003")
SCRIPTWRITER_A2A_URL = os.getenv("SCRIPTWRITER_A2A_URL", "http://localhost:8004")
GUEST_A2A_URL = os.getenv("GUEST_A2A_URL", "http://localhost:8005")
AUDIO_PRODUCER_A2A_URL = os.getenv("AUDIO_PRODUCER_A2A_URL", "http://localhost:8006")
EVALUATOR_A2A_URL = os.getenv("EVALUATOR_A2A_URL", "http://localhost:8007")
EDITOR_A2A_URL = os.getenv("EDITOR_A2A_URL", "http://localhost:8008")
PUBLISHER_A2A_URL = os.getenv("PUBLISHER_A2A_URL", "http://localhost:8009")

# Ingest Agent configuration
INGEST_CONFIG = {
    "max_chunks": 20,  # Increased for large articles (40K+ characters)
    "chunk_size": 5000,  # characters (increased from 1000 to 5000)
    "chunk_overlap": 500,  # characters (increased for better context)
}

def get_config() -> Dict[str, Any]:
    """Get application configuration"""
    return {
        "gemini_api_key": GEMINI_API_KEY,
        "gemini_model": GEMINI_MODEL,
        "google_cloud_project": GOOGLE_CLOUD_PROJECT,
        "vertex_ai_location": VERTEX_AI_LOCATION,
        "kg_provider": KG_PROVIDER,
        "kg_builder_a2a_url": KG_BUILDER_A2A_URL,
        "topic_discovery_a2a_url": TOPIC_DISCOVERY_A2A_URL,
        "scriptwriter_a2a_url": SCRIPTWRITER_A2A_URL,
        "guest_a2a_url": GUEST_A2A_URL,
        "audio_producer_a2a_url": AUDIO_PRODUCER_A2A_URL,
        "evaluator_a2a_url": EVALUATOR_A2A_URL,
        "editor_a2a_url": EDITOR_A2A_URL,
        "publisher_a2a_url": PUBLISHER_A2A_URL,
        "ingest": INGEST_CONFIG,
    }

