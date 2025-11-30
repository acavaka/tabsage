#!/usr/bin/env python3
"""
Script for generating audio podcast from all articles in Firestore

This script creates a single audio podcast by combining information from all
articles stored in Firestore Knowledge Graph.

Process:
1. Gets all articles from Firestore
2. Generates podcast script via Scriptwriter Agent
3. Creates audio via Audio Producer Agent + Google Cloud TTS
4. Saves audio file

Usage:
    export KG_PROVIDER=firestore
    export GOOGLE_CLOUD_PROJECT=your-project-id
    python scripts/generate_podcast_all.py

Requirements:
    - Google Cloud project configured
    - Firestore configured
    - GEMINI_API_KEY set in config.py
    - Google Cloud Text-to-Speech API configured
    - Processed articles in Firestore

Example output:
    ============================================================
    🎙️ GENERATING AUDIO SUMMARY FROM ALL ARTICLES
    ============================================================
    
    📚 Found 15 articles in Firestore
    🎙️ Starting audio summary generation from 15 articles...
    
    ============================================================
    📊 GENERATION RESULTS
    ============================================================
    
    ✅ Audio summary successfully created!
    
    📁 File path: /path/to/audio_summary_20251129_120000.mp3
    ⏱️  Duration: 1250.5 seconds (20.8 minutes)
    📚 Articles used: 15
    
    📋 Used articles:
       1. https://habr.com/ru/articles/...
       2. https://habr.com/ru/articles/...
       ...
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path

from tools.kg_client import get_kg_instance
from tools.audio_summary import generate_audio_summary
from observability.logging import get_logger

logger = get_logger(__name__)


async def generate_podcast_from_all_articles():
    """
    Generates podcast from all articles in Firestore
    
    Process:
    1. Connects to Firestore Knowledge Graph
    2. Gets all articles from "articles" collection
    3. Generates single audio podcast by combining information from all articles
    4. Saves audio file
    
    Returns:
        Dictionary with generation result:
        {
            "status": "success" | "error",
            "audio_path": str,  # Path to created audio file
            "duration_seconds": float,  # Duration in seconds
            "articles_count": int,  # Number of articles used
            "articles_used": List[str]  # List of URLs of used articles
        }
    """
    try:
        kg = get_kg_instance()
        
        if not hasattr(kg, 'db'):
            logger.error("❌ Firestore not available")
            logger.error("💡 Set KG_PROVIDER=firestore and configure Google Cloud project")
            return {"status": "error", "error": "Firestore not available"}
        
        logger.info("📚 Getting articles from Firestore...")
        articles_ref = kg.db.collection("articles")
        article_urls = []
        articles_data = []
        
        for article_doc in articles_ref.stream():
            article_data = article_doc.to_dict()
            url = article_data.get("url")
            if url:
                article_urls.append(url)
                articles_data.append(article_data)
        
        logger.info(f"✅ Found {len(article_urls)} articles in Firestore")
        
        if not article_urls:
            logger.warning("⚠️  No articles in Firestore for podcast generation")
            logger.info("💡 First process articles via:")
            logger.info("   - Telegram bot (send URL)")
            logger.info("   - examples/process_urls.py")
            logger.info("   - scripts/reprocess_articles.py")
            return {"status": "error", "error": "No articles found in Firestore"}
        
        logger.info(f"🎙️ Starting audio summary generation from {len(article_urls)} articles...")
        logger.info("   This may take several minutes...")
        
        episode_id = f"all_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = await generate_audio_summary(
            article_urls=article_urls,
            session_id="audio_summary_all_articles",
            episode_id=episode_id
        )
        
        return result
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Error generating podcast: {e}")
        logger.debug(traceback.format_exc())
        logger.error("💡 Troubleshooting:")
        logger.error("   - Check Google Cloud project settings")
        logger.error("   - Make sure Firestore is configured correctly")
        logger.error("   - Check access to Google Cloud Text-to-Speech API")
        return {"status": "error", "error": str(e)}


async def main():
    """
    Main script function
    
    Initializes environment and starts podcast generation
    """
    os.environ.setdefault("KG_PROVIDER", "firestore")
    
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        logger.error("GOOGLE_CLOUD_PROJECT environment variable is required")
        logger.info("💡 Please set it in .env file or export it:")
        logger.info("   export GOOGLE_CLOUD_PROJECT=your-project-id")
        sys.exit(1)
    
    print("=" * 70)
    print("🎙️ GENERATING AUDIO SUMMARY FROM ALL ARTICLES")
    print("=" * 70)
    print()
    print("This script will create a single audio podcast from all articles in Firestore.")
    print()
    print("💡 Process:")
    print("   1. Getting all articles from Firestore")
    print("   2. Generating podcast script via Scriptwriter Agent")
    print("   3. Creating audio via Audio Producer Agent + Google Cloud TTS")
    print("   4. Saving audio file")
    print()
    print("-" * 70)
    print()
    
    # Generate podcast
    result = await generate_podcast_from_all_articles()
    
    # Output results
    print()
    print("=" * 70)
    print("📊 GENERATION RESULTS")
    print("=" * 70)
    print()
    
    if result.get("status") == "success":
        print("✅ Audio summary successfully created!")
        print()
        print("📁 File information:")
        audio_path = result.get('audio_path', 'N/A')
        duration_seconds = result.get('duration_seconds', 0)
        duration_minutes = duration_seconds / 60
        articles_count = result.get('articles_count', 0)
        
        print(f"   📂 Path: {audio_path}")
        print(f"   ⏱️  Duration: {duration_seconds:.1f} sec ({duration_minutes:.1f} min)")
        print(f"   📚 Articles used: {articles_count}")
        print()
        
        # Show used articles
        articles_used = result.get('articles_used', [])
        if articles_used:
            print("📋 Used articles:")
            print("-" * 70)
            for i, url in enumerate(articles_used[:10], 1):
                print(f"   {i:2d}. {url}")
            if len(articles_used) > 10:
                print(f"   ... and {len(articles_used) - 10} more articles")
            print()
        
        print("💡 Next steps:")
        print(f"   - Listen to file: {audio_path}")
        print("   - Send via Telegram:")
        print(f"     python scripts/send_audio_to_telegram.py {audio_path}")
    else:
        error_msg = result.get('error_message', result.get('error', 'Unknown error'))
        print(f"❌ Error: {error_msg}")
        print()
        print("💡 Troubleshooting:")
        print("   - Check that Firestore has processed articles")
        print("   - Make sure Google Cloud project is configured")
        print("   - Check access to Google Cloud Text-to-Speech API")
        print("   - Check GEMINI_API_KEY in config.py")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

