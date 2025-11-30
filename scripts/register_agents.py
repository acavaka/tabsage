#!/usr/bin/env python3
"""
Script to register all agents in Vertex AI Agent Registry

This script registers all TabSage agents in Vertex AI Agent Registry,
which allows:
- Discovering agents via registry
- Using agents from other projects
- Managing agent versions
- Tracking agent usage

Usage:
    python3 scripts/register_agents.py

Requirements:
    - Google Cloud project configured
    - GEMINI_API_KEY set in config.py
    - Application Default Credentials configured (gcloud auth application-default login)
    - All project dependencies installed

Example result:
    ============================================================
    📋 Registering TabSage agents in Vertex AI Registry
    ============================================================
    
    ============================================================
    📊 REGISTRATION RESULTS
    ============================================================
    
    Total agents: 8
    Successfully registered: 8 ✅
    Errors: 0 ❌
    
      ✅ ingest_agent: success
         URL: https://vertex-ai-agent-registry.googleapis.com/...
         Version: 0.1.0
      ✅ kg_builder_agent: success
         ...
    
    ============================================================
    ✅ Registration completed!
    ============================================================
"""

import sys
from pathlib import Path

# Add src to path for importing project modules

from registry.vertex_ai_registry import register_all_agents
from observability.setup import setup_observability


def main():
    """
    Registers all TabSage agents in Vertex AI Agent Registry
    
    Process:
    1. Initializes observability (metrics, logging)
    2. Registers all agents in registry
    3. Outputs registration results
    
    Returns:
        0 on successful registration of all agents, 1 on errors
    """
    print("=" * 70)
    print("📋 Registering TabSage agents in Vertex AI Registry")
    print("=" * 70)
    print()
    print("This script will register the following agents:")
    print("   • Ingest Agent")
    print("   • KG Builder Agent")
    print("   • Topic Discovery Agent")
    print("   • Scriptwriter Agent")
    print("   • Guest Agent")
    print("   • Audio Producer Agent")
    print("   • Evaluator Agent")
    print("   • Publisher Agent")
    print()
    print("💡 Make sure:")
    print("   - Google Cloud project is configured")
    print("   - Run: gcloud auth application-default login")
    print("   - GEMINI_API_KEY is set")
    print()
    print("-" * 70)
    print()
    
    # Initialize observability
    # Sets up metrics, logging and tracing for tracking agent work
    print("📊 Initializing observability...")
    setup_observability(metrics_port=8001)
    print("✅ Observability configured")
    print()
    
    # Register all agents
    # register_all_agents() registers all agents from project
    print("📝 Registering agents...")
    print()
    results = register_all_agents()
    
    # Output results
    print()
    print("=" * 70)
    print("📊 REGISTRATION RESULTS")
    print("=" * 70)
    print()
    
    # Calculate statistics
    success_count = sum(1 for r in results.values() if r.get("status") == "success")
    total_count = len(results)
    failed_count = total_count - success_count
    
    print(f"📈 Statistics:")
    print(f"   Total agents: {total_count}")
    print(f"   ✅ Successfully registered: {success_count}")
    print(f"   ❌ Errors: {failed_count}")
    print()
    
    # Detailed information for each agent
    if results:
        print("📋 Registration details:")
        print("-" * 70)
        for agent_name, result in results.items():
            status_icon = "✅" if result.get("status") == "success" else "❌"
            status_text = result.get('status', 'unknown')
            print(f"   {status_icon} {agent_name}: {status_text}")
            
            if result.get("status") == "success":
                agent_info = result.get("agent_info", {})
                url = agent_info.get('url', 'N/A')
                version = agent_info.get('version', 'N/A')
                print(f"      📍 URL: {url}")
                print(f"      📦 Version: {version}")
            else:
                error = result.get('error', result.get('error_message', 'Unknown error'))
                print(f"      ❌ Error: {error}")
            print()
    
    print("=" * 70)
    if success_count == total_count:
        print("✅ Registration completed successfully!")
        print()
        print("💡 Agents are now available via Vertex AI Agent Registry")
        print("   Use registry to discover and use agents")
    else:
        print("⚠️  Registration completed with errors")
        print()
        print("💡 Troubleshooting:")
        print("   - Check Google Cloud project settings")
        print("   - Make sure authentication is done: gcloud auth application-default login")
        print("   - Check access rights to Vertex AI Agent Registry")
    print("=" * 70)
    
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())

