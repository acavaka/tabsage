"""
Orchestrator Usage Example for Complete Pipeline

This example demonstrates using Orchestrator to coordinate
all agents in a unified text processing pipeline.

Orchestrator provides:
- Single entry point for pipeline execution
- Automatic coordination of all agents
- Error handling and retry logic
- Human-in-the-loop (HITL) support
- Episode history tracking

Run:
    python examples/orchestrator_example.py

Requirements:
    - GEMINI_API_KEY set in config.py
    - All project dependencies installed

Example result:
    ✅ Pipeline Completed Successfully!
    📊 Results Summary:
       - Ingest: Artificial Intelligence in Medicine
       - KG Builder: 15 entities
       - Topics: 3 topics
       - Script segments: 8 segments
       - TTS prompts: 8 prompts
       - Published: True
"""

import asyncio
import os
import sys

# Add path to src for importing project modules

from core.orchestrator import Orchestrator
from core.config import GEMINI_API_KEY


async def main():
    """Orchestrator usage example"""
    
    print("🚀 TabSage Orchestrator - Complete Pipeline\n")
    print("=" * 70)
    
    # Create Orchestrator
    orchestrator = Orchestrator(config={
        "max_retries": 3,
        "enable_hitl": True  # Enable human-in-loop
    })
    
    # Sample text
    sample_text = """
    Artificial Intelligence in Medicine: Revolution in Diagnosis
    
    Google Health company developed a new algorithm for disease diagnosis based on machine learning.
    Researchers from Stanford University conducted large-scale clinical trials of this algorithm.
    Results showed 30% improvement in diagnostic accuracy compared to traditional methods.
    
    Dr. Smith from Mayo Clinic commented: "This is a revolutionary breakthrough in medical diagnosis".
    Technology is already being used in clinics in Boston and New York with positive results.
    
    Professor Johnson from MIT noted the importance of ethical aspects of using AI in medicine.
    It is necessary to ensure algorithm transparency and patient data protection.
    """
    
    episode_id = "orchestrator_episode_001"
    session_id = "orchestrator_session_001"
    
    print(f"\n📋 Episode ID: {episode_id}")
    print(f"📋 Session ID: {session_id}\n")
    
    # Run complete pipeline
    print("⚙️  Running complete pipeline...\n")
    
    result = await orchestrator.run_pipeline(
        raw_text=sample_text,
        episode_id=episode_id,
        session_id=session_id,
        metadata={"source": "orchestrator_example"}
    )
    
    # Print results
    if result.get("status") == "completed":
        print("\n" + "=" * 70)
        print("\n✅ Pipeline Completed Successfully!\n")
        
        print("📊 Results Summary:")
        print(f"   - Ingest: {result.get('ingest', {}).get('title', 'N/A')}")
        print(f"   - KG Builder: {len(result.get('kg_builder', {}).get('entities', []))} entities")
        print(f"   - Topics: {len(result.get('topic_discovery', {}).get('topics', []))}")
        print(f"   - Script segments: {len(result.get('scriptwriter', {}).get('segments', []))}")
        print(f"   - TTS prompts: {len(result.get('audio_producer', {}).get('tts_prompts', []))}")
        print(f"   - Published: {result.get('publisher', {}).get('published', False)}")
        
        # Episode history
        print("\n📜 Episode History:")
        history = orchestrator.get_episode_history(episode_id)
        for key, value in history.items():
            print(f"   {key}: {value}")
    else:
        print(f"\n❌ Pipeline Failed: {result.get('error_message', 'Unknown error')}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

