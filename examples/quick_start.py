"""
Quick Start Example for Ingest Agent

This example demonstrates basic usage of Ingest Agent for text processing:
- Text normalization (ad removal, formatting)
- Chunking
- Language detection
- Brief summary generation

Run:
    python examples/quick_start.py

Requirements:
    - GEMINI_API_KEY set in config.py or environment variables
    - All project dependencies installed

Example result:
    ✅ Processing complete!
    📤 Output:
       Title: Scientific discoveries in artificial intelligence
       Language: en
       Summary: Researchers announced a breakthrough in machine learning...
       Chunks: 2
       Cleaned text length: 245 characters
"""

import asyncio
import os
import sys

# Add path to src for importing project modules

from agents.ingest_agent import run_once, create_ingest_agent
# Import config so key is set in environment
from core.config import GEMINI_API_KEY

# Key is now taken from config.py, no check needed


async def main():
    """
    Main function for Ingest Agent usage example
    
    Demonstrates:
    1. Input data preparation (raw_text, metadata)
    2. Calling Ingest Agent via run_once()
    3. Result processing (title, language, chunks, summary)
    
    Expected result:
    - Text normalized (ads removed)
    - Text chunked (max 5 by default)
    - Language detected
    - Title and brief summary generated
    """
    
    print("🚀 TabSage Ingest Agent - Quick Start\n")
    print("=" * 60)
    
    # Sample text for processing
    # Includes ads that Ingest Agent should remove
    sample_text = """
    Scientific discoveries in artificial intelligence
    
    Researchers from leading universities announced a breakthrough in machine learning.
    The new algorithm shows 40% performance improvement compared to previous methods.
    
    [Ad: Subscribe to our AI course]
    
    Experts believe this discovery could revolutionize the approach to training neural networks.
    Application of the new method has already shown results in computer vision and natural language processing tasks.
    """
    
    # Create payload for Ingest Agent
    # payload contains all necessary data for processing
    payload = {
        "raw_text": sample_text,  # Raw text for processing
        "metadata": {  # Article metadata
            "source": "example",
            "type": "article"
        },
        "session_id": "quick_start_session",  # Session ID for tracking
        "episode_id": "episode_001"  # Episode/article ID
    }
    
    print("📥 Input payload:")
    print(f"   Session ID: {payload['session_id']}")
    print(f"   Episode ID: {payload['episode_id']}")
    print(f"   Text length: {len(payload['raw_text'])} characters")
    print(f"   Contains ads: {'[Ad' in payload['raw_text']}\n")
    
    # Process through Ingest Agent
    # Ingest Agent performs:
    # - Text normalization (ad removal, formatting)
    # - Chunking (max 5 by default)
    # - Language detection
    # - Title and summary generation
    print("⚙️  Processing through Ingest Agent...")
    print("   - Normalizing text (removing ads, formatting)...")
    print("   - Chunking text...")
    print("   - Detecting language...")
    print("   - Generating title and summary...\n")
    
    result = await run_once(payload)
    
    # Print processing results
    if "error_message" in result:
        print(f"❌ Error: {result['error_message']}")
        print("\n💡 Tips:")
        print("   - Check GEMINI_API_KEY in config.py")
        print("   - Make sure all dependencies are installed")
        print("   - Check internet connection")
    else:
        print("✅ Processing complete!\n")
        print("=" * 60)
        print("📤 Output Results:")
        print("=" * 60)
        print(f"\n📝 Title: {result.get('title', 'N/A')}")
        print(f"🌐 Language: {result.get('language', 'N/A')}")
        print(f"📄 Summary: {result.get('summary', 'N/A')[:150]}...")
        print(f"📦 Chunks: {len(result.get('chunks', []))}")
        
        # Show chunk details
        chunks = result.get('chunks', [])
        if chunks:
            print(f"\n📋 Chunks details:")
            for i, chunk in enumerate(chunks, 1):
                chunk_preview = chunk[:100] + "..." if len(chunk) > 100 else chunk
                print(f"   {i}. [{len(chunk)} chars] {chunk_preview}")
        
        # Show cleaned text statistics
        cleaned_text = result.get('cleaned_text', '')
        print(f"\n🧹 Cleaned text:")
        print(f"   Length: {len(cleaned_text)} characters")
        print(f"   Ads removed: {'[Ad' not in cleaned_text}")
        print(f"   Session ID: {result.get('session_id')}")
        print(f"   Episode ID: {result.get('episode_id')}")
        
        print("\n" + "=" * 60)
        print("✅ Example completed successfully!")
        print("\n💡 Next steps:")
        print("   - Try examples/kg_builder_example.py for full pipeline")
        print("   - Check examples/process_urls.py for URL processing")


if __name__ == "__main__":
    asyncio.run(main())

