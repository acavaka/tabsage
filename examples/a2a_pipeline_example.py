"""Full A2A pipeline example: Ingest -> KG Builder"""

import asyncio
import os
import sys
import subprocess
import time
import requests

# Add path to src

from agents.ingest_agent_a2a import run_once_with_a2a
from core.config import GEMINI_API_KEY


def start_kg_builder_server():
    """Starts KG Builder A2A server in background"""
    server_script = os.path.join(
        os.path.dirname(__file__),
        "..",
        "services",
        "a2a",
        "kg_builder_server.py"
    )
    
    process = subprocess.Popen(
        [sys.executable, server_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "GOOGLE_API_KEY": GEMINI_API_KEY}
    )
    
    # Wait for server to start
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                "http://localhost:8002/.well-known/agent-card.json",
                timeout=1
            )
            if response.status_code == 200:
                print("✅ KG Builder A2A server is running!")
                return process
        except requests.exceptions.RequestException:
            time.sleep(1)
            print(".", end="", flush=True)
    
    print("\n⚠️  Server may not be ready yet")
    return process


async def main():
    """A2A pipeline usage example"""
    
    print("🚀 TabSage A2A Pipeline: Ingest -> KG Builder\n")
    print("=" * 60)
    
    # Start KG Builder A2A server
    print("\n📡 Starting KG Builder A2A server...")
    server_process = start_kg_builder_server()
    
    if server_process is None:
        print("❌ Failed to start KG Builder server")
        return
    
    try:
        # Give server time to fully start
        await asyncio.sleep(2)
        
        # Step 1: Ingest Agent with A2A integration
        print("\n" + "=" * 60)
        print("\n📥 Step 1: Ingest Agent -> KG Builder (via A2A)\n")
        
        sample_text = """
        Artificial Intelligence in Medicine
        
        Google Health company developed a new algorithm for disease diagnosis.
        Researchers from Stanford University conducted clinical trials.
        Results showed 30% improvement in diagnostic accuracy.
        
        Dr. Smith from Mayo Clinic commented: "This is a revolutionary breakthrough".
        Technology is already being used in clinics in Boston and New York.
        """
        
        payload = {
            "raw_text": sample_text,
            "metadata": {"source": "example", "type": "article"},
            "session_id": "a2a_pipeline_session",
            "episode_id": "episode_001"
        }
        
        result = await run_once_with_a2a(payload, kg_builder_url="http://localhost:8002")
        
        if "error_message" in result:
            print(f"❌ Error: {result['error_message']}")
        else:
            print("✅ Pipeline complete!")
            print(f"\n📊 Results:")
            print(f"   Title: {result.get('title')}")
            print(f"   Language: {result.get('language')}")
            print(f"   Chunks: {len(result.get('chunks', []))}")
            print(f"   KG Builder called: {result.get('kg_builder_called', False)}")
            
            if result.get('kg_builder_error'):
                print(f"   ⚠️  KG Builder error: {result.get('kg_builder_error')}")
    
    finally:
        # Stop server
        if server_process:
            server_process.terminate()
            server_process.wait()
            print("\n🛑 KG Builder server stopped")


if __name__ == "__main__":
    asyncio.run(main())

