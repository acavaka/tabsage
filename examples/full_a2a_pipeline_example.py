"""
Full TabSage Pipeline Example via A2A Protocol

This example demonstrates using Agent-to-Agent (A2A) communication
to run a complete text processing pipeline through remote agents.

A2A protocol allows:
- Running agents as separate services
- Horizontal system scaling
- Replacing agent implementations without code changes
- Using agents on different machines

Run:
    1. Start all A2A servers:
       python scripts/start_all_a2a_servers.py
    
    2. Run example:
       python examples/full_a2a_pipeline_example.py

Requirements:
    - All A2A servers must be running
    - GEMINI_API_KEY set in config.py
    - Ports 8002-8009 must be free

Example result:
    ✅ Pipeline completed successfully!
    Episode ID: episode_a2a_001
    Ingest: Artificial Intelligence in Medicine
    KG Builder: 15 entities extracted
    Topic Discovery: 3 topics found
    Scriptwriter: 8 segments generated
    Publisher: True
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add path to src for importing project modules

from core.orchestrator_a2a import A2AOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    Runs complete pipeline via A2A protocol
    
    Process:
    1. Creates A2A Orchestrator to coordinate agents
    2. Sends text for processing
    3. Orchestrator coordinates all agents via A2A
    4. Returns complete pipeline results
    
    Expected result:
    - Ingest: text normalization and chunking
    - KG Builder: entity and relationship extraction
    - Topic Discovery: topic discovery for podcast
    - Scriptwriter: podcast script generation
    - Audio Producer: audio prompt generation
    - Evaluator: content quality evaluation
    - Publisher: result publication
    """
    
    # Sample text for processing
    # Text contains information about AI, ML, Deep Learning and Transformers
    sample_text = """
    Artificial Intelligence (AI) is a field of computer science that deals with creating 
    intelligent machines capable of performing tasks that typically require human intelligence.
    
    Machine Learning is a subset of AI that allows systems to automatically learn 
    and improve from experience without explicit programming.
    
    Deep Learning uses neural networks with multiple layers to model and understand 
    complex patterns in data.
    
    Transformers are a neural network architecture that revolutionized natural language processing, 
    starting with BERT and GPT models.
    """
    
    # Create A2A Orchestrator
    # Orchestrator coordinates all agents via A2A protocol
    # Each agent works as a separate service on its own port
    orchestrator = A2AOrchestrator(use_a2a=True)
    
    # Unique identifiers for tracking processing
    episode_id = "episode_a2a_001"
    session_id = "session_a2a_001"
    
    logger.info("=" * 70)
    logger.info(f"🚀 Starting A2A pipeline")
    logger.info(f"   Episode ID: {episode_id}")
    logger.info(f"   Session ID: {session_id}")
    logger.info("=" * 70)
    
    # Run complete pipeline via A2A
    # Orchestrator automatically calls all necessary agents
    result = await orchestrator.run_pipeline(
        raw_text=sample_text,
        episode_id=episode_id,
        session_id=session_id,
        metadata={"source": "example", "language": "en"}
    )
    
    # Process results
    if result.get("status") == "completed":
        logger.info("\n" + "=" * 70)
        logger.info("✅ Pipeline completed successfully!")
        logger.info("=" * 70)
        logger.info(f"\n📋 Episode ID: {result.get('episode_id')}")
        logger.info(f"📦 Results keys: {list(result.keys())}\n")
        
        # Print detailed information about each agent's results
        logger.info("📊 Pipeline Results:")
        logger.info("-" * 70)
        
        if "ingest" in result:
            ingest = result['ingest']
            logger.info(f"   📥 Ingest:")
            logger.info(f"      Title: {ingest.get('title', 'N/A')}")
            logger.info(f"      Language: {ingest.get('language', 'N/A')}")
            logger.info(f"      Chunks: {len(ingest.get('chunks', []))}")
        
        if "kg_builder" in result:
            kg = result['kg_builder']
            entities_count = len(kg.get('entities', []))
            relations_count = len(kg.get('relations', []))
            logger.info(f"   🔗 KG Builder:")
            logger.info(f"      Entities: {entities_count}")
            logger.info(f"      Relations: {relations_count}")
        
        if "topic_discovery" in result:
            topics = result['topic_discovery']
            topics_count = len(topics.get('topics', []))
            logger.info(f"   🔍 Topic Discovery:")
            logger.info(f"      Topics found: {topics_count}")
        
        if "scriptwriter" in result:
            script = result['scriptwriter']
            segments_count = len(script.get('segments', []))
            logger.info(f"   ✍️  Scriptwriter:")
            logger.info(f"      Segments: {segments_count}")
            logger.info(f"      Estimated length: {script.get('total_estimated_minutes', 0)} min")
        
        if "audio_producer" in result:
            audio = result['audio_producer']
            logger.info(f"   🎙️  Audio Producer:")
            logger.info(f"      TTS prompts: {len(audio.get('tts_prompts', []))}")
        
        if "evaluator" in result:
            eval_result = result['evaluator']
            logger.info(f"   ✅ Evaluator:")
            logger.info(f"      Quality score: {eval_result.get('quality_score', 'N/A')}")
        
        if "publisher" in result:
            publisher = result['publisher']
            logger.info(f"   📤 Publisher:")
            logger.info(f"      Published: {publisher.get('published', False)}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ A2A Pipeline Example Completed!")
        logger.info("=" * 70)
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ Pipeline failed!")
        logger.error("=" * 70)
        logger.error(f"Error: {result.get('error_message', 'Unknown error')}")
        logger.error("\n💡 Troubleshooting:")
        logger.error("   - Check that all A2A servers are running")
        logger.error("   - Make sure ports 8002-8009 are free")
        logger.error("   - Check GEMINI_API_KEY in config.py")
        return 1
    
    return 0


if __name__ == "__main__":
    print("=" * 60)
    print("TabSage Full A2A Pipeline Example")
    print("=" * 60)
    print()
    print("⚠️  WARNING: Before running, make sure all A2A servers are running:")
    print("  - KG Builder: http://localhost:8002")
    print("  - Topic Discovery: http://localhost:8003")
    print("  - Scriptwriter: http://localhost:8004")
    print("  - Guest: http://localhost:8005")
    print("  - Audio Producer: http://localhost:8006")
    print("  - Evaluator: http://localhost:8007")
    print("  - Editor: http://localhost:8008")
    print("  - Publisher: http://localhost:8009")
    print()
    print("To start all servers use:")
    print("  python3 scripts/start_all_a2a_servers.py")
    print()
    print("=" * 60)
    print()
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

