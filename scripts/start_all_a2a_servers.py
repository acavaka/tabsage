"""
Script to start all A2A (Agent-to-Agent) servers

This script starts all TabSage A2A servers in separate processes.
A2A protocol allows agents to communicate via HTTP API, providing:
- Horizontal scaling
- Independent agent deployment
- Implementation replacement without code changes
- Using agents on different machines

Usage:
    python scripts/start_all_a2a_servers.py

Requirements:
    - GEMINI_API_KEY set in config.py
    - Ports 8002-8009 must be free
    - All project dependencies installed

Servers to start:
    - KG Builder: http://localhost:8002
    - Topic Discovery: http://localhost:8003
    - Scriptwriter: http://localhost:8004
    - Guest: http://localhost:8005
    - Audio Producer: http://localhost:8006
    - Evaluator: http://localhost:8007
    - Editor: http://localhost:8008
    - Publisher: http://localhost:8009

Example output:
    ============================================================
    Starting all TabSage A2A servers
    ============================================================
    
    🚀 Starting KG Builder server on port 8002...
    🚀 Starting Topic Discovery server on port 8003...
    ...
    
    ✅ All servers started!
    
    Servers running:
      - KG Builder
      - Topic Discovery
      - Scriptwriter
      - Guest
      - Audio Producer
      - Evaluator
      - Editor
      - Publisher
    
    Press Ctrl+C to stop all servers
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Add path to src for importing project modules
project_root = Path(__file__).parent.parent

# Configuration of all A2A servers
# Each server runs on its own port and provides HTTP API
servers = [
    {
        "name": "KG Builder",
        "module": "src.tabsage.services.a2a.kg_builder_server",
        "port": 8002,
        "description": "Extracting entities and relationships from text"
    },
    {
        "name": "Topic Discovery",
        "module": "src.tabsage.services.a2a.topic_discovery_server",
        "port": 8003,
        "description": "Discovering topics for podcasts"
    },
    {
        "name": "Scriptwriter",
        "module": "src.tabsage.services.a2a.scriptwriter_server",
        "port": 8004,
        "description": "Generating podcast scripts"
    },
    {
        "name": "Guest",
        "module": "src.tabsage.services.a2a.guest_server",
        "port": 8005,
        "description": "Generating personas for podcasts"
    },
    {
        "name": "Audio Producer",
        "module": "src.tabsage.services.a2a.audio_producer_server",
        "port": 8006,
        "description": "Generating audio prompts for TTS"
    },
    {
        "name": "Evaluator",
        "module": "src.tabsage.services.a2a.evaluator_server",
        "port": 8007,
        "description": "Evaluating content quality"
    },
    {
        "name": "Editor",
        "module": "src.tabsage.services.a2a.editor_server",
        "port": 8008,
        "description": "Content editing and improvement"
    },
    {
        "name": "Publisher",
        "module": "src.tabsage.services.a2a.publisher_server",
        "port": 8009,
        "description": "Publishing results"
    },
]


def start_server(server_info):
    """
    Starts one A2A server in separate process
    
    Args:
        server_info: Dictionary with server information (name, module, port)
        
    Returns:
        subprocess.Popen object of started process
    """
    print(f"🚀 Starting {server_info['name']} server on port {server_info['port']}...")
    print(f"   {server_info.get('description', '')}")
    
    # Start server as separate Python process
    # Use module directly via -m flag
    process = subprocess.Popen(
        [sys.executable, "-m", server_info["module"]],
        cwd=str(project_root),  # Working directory - project root
        stdout=subprocess.PIPE,  # Redirect stdout
        stderr=subprocess.PIPE   # Redirect stderr
    )
    return process


def main():
    """
    Main function - starts all A2A servers
    
    Process:
    1. Starts each server in separate process
    2. Waits for all processes to complete
    3. Handles Ctrl+C for graceful shutdown
    4. Stops all servers on error
    
    Returns:
        0 on successful completion, 1 on error
    """
    print("=" * 70)
    print("🚀 Starting all TabSage A2A servers")
    print("=" * 70)
    print()
    print("This script will start the following servers:")
    for server in servers:
        print(f"   • {server['name']} - http://localhost:{server['port']}")
    print()
    print("💡 Press Ctrl+C to stop all servers")
    print()
    print("-" * 70)
    print()
    
    processes = []  # List of started processes
    
    try:
        # Start each server
        for server in servers:
            process = start_server(server)
            processes.append((server["name"], process))
            time.sleep(1)  # Small delay between starts for stability
        
        print()
        print("=" * 70)
        print("✅ All servers started!")
        print("=" * 70)
        print()
        print("📋 Servers running:")
        for name, _ in processes:
            print(f"   ✅ {name}")
        print()
        print("💡 Tips:")
        print("   - Check server status: curl http://localhost:8002/.well-known/agent-card.json")
        print("   - Use examples/full_a2a_pipeline_example.py for testing")
        print("   - Press Ctrl+C to stop all servers")
        print()
        print("=" * 70)
        
        # Wait for all processes to complete
        # In normal mode servers run indefinitely
        try:
            for name, process in processes:
                process.wait()  # Wait for process completion
        except KeyboardInterrupt:
            # Handle Ctrl+C for graceful shutdown
            print("\n" + "=" * 70)
            print("🛑 Stopping all servers...")
            print("=" * 70)
            print()
            
            for name, process in processes:
                print(f"   🛑 Stopping {name}...")
                process.terminate()  # Send SIGTERM
                try:
                    process.wait(timeout=5)  # Wait for completion (max 5 sec)
                    print(f"   ✅ {name} stopped")
                except subprocess.TimeoutExpired:
                    print(f"   ⚠️  {name} did not stop, forcing termination...")
                    process.kill()  # Force termination
                    process.wait()
                    print(f"   ✅ {name} killed")
            
            print()
            print("=" * 70)
            print("✅ All servers stopped")
            print("=" * 70)
    
    except Exception as e:
        # Handle errors on startup
        print("\n" + "=" * 70)
        print(f"❌ Error: {e}")
        print("=" * 70)
        print()
        print("🛑 Stopping all servers due to error...")
        
        # Stop all processes on error
        for name, process in processes:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        print("✅ All servers stopped")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

