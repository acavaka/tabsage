"""A2A Server for Topic Discovery Agent"""

import os
import sys

# Add path to src

from agents.topic_discovery_a2a_agent import create_topic_discovery_a2a_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create Topic Discovery Agent for A2A
topic_discovery_agent = create_topic_discovery_a2a_agent()

# Expose via A2A
app = to_a2a(topic_discovery_agent, port=int(os.getenv('PORT', 8003)))

if __name__ == "__main__" or os.getenv('AGENT_SERVER'):
    import uvicorn
    uvicorn.run(app, host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 8003)))

