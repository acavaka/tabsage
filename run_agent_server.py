#!/usr/bin/env python3
"""
Entrypoint script for running A2A agent servers on Cloud Run

Usage:
    AGENT_SERVER=services/a2a/kg_builder_server.py python run_agent_server.py
"""

import os
import sys

# Get agent server file from environment
agent_server = os.getenv('AGENT_SERVER')

if not agent_server:
    print("Error: AGENT_SERVER environment variable not set")
    print("Example: AGENT_SERVER=services/a2a/kg_builder_server.py")
    sys.exit(1)

if not os.path.exists(agent_server):
    print(f"Error: Agent server file not found: {agent_server}")
    sys.exit(1)

# Set environment variable so server knows to run
os.environ['AGENT_SERVER'] = agent_server

# Import and execute the server file
# This will trigger uvicorn.run() because of the condition we added
print(f"Starting agent server: {agent_server}")

try:
    with open(agent_server, 'r') as f:
        code = compile(f.read(), agent_server, 'exec')
        exec(code, {'__name__': '__main__', '__file__': agent_server, '__package__': None})
except Exception as e:
    print(f"Error starting server: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
