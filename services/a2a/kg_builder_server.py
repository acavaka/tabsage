"""A2A Server for KG Builder Agent"""

import os
import sys

from agents.kg_builder_a2a_agent import create_kg_builder_a2a_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create KG Builder Agent for A2A
kg_builder_agent = create_kg_builder_a2a_agent()

# Cloud Run compatibility: use PORT env var if set
PORT = int(os.getenv('PORT', 8002))
HOST = os.getenv('HOST', '0.0.0.0')

# Expose via A2A
app = to_a2a(kg_builder_agent, port=PORT)

# Always run uvicorn (for Cloud Run)
if __name__ == "__main__" or os.getenv('AGENT_SERVER'):
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)

