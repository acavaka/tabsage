"""A2A Server for Publisher Agent"""

import os
import sys

# Add path to src

from agents.publisher_a2a_agent import create_publisher_a2a_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create Publisher Agent for A2A
publisher_agent = create_publisher_a2a_agent()

# Expose via A2A
app = to_a2a(publisher_agent, port=int(os.getenv('PORT', 8009)))

if __name__ == "__main__" or os.getenv('AGENT_SERVER'):
    import uvicorn
    uvicorn.run(app, host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 8009)))

