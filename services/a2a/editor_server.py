"""A2A Server for Editor Agent"""

import os
import sys

# Add path to src

from agents.editor_a2a_agent import create_editor_a2a_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create Editor Agent for A2A
editor_agent = create_editor_a2a_agent()

# Expose via A2A
app = to_a2a(editor_agent, port=int(os.getenv('PORT', 8008)))

if __name__ == "__main__" or os.getenv('AGENT_SERVER'):
    import uvicorn
    uvicorn.run(app, host=os.getenv('HOST', '0.0.0.0'), port=int(os.getenv('PORT', 8008)))

