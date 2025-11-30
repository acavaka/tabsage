"""
Quick demonstration of URL processing through TabSage pipeline

This example demonstrates quick processing of multiple article URLs:
1. Content download via Web Scraper
2. Processing via Ingest Agent (normalization, chunking)
3. Knowledge extraction via KG Builder Agent

Run:
    python examples/process_urls_quick.py

Requirements:
    - GEMINI_API_KEY set in config.py
    - Internet access for downloading articles
    - All project dependencies installed

Example result:
    ✅ Downloaded: 5234 characters
    ✅ Ingest: Article title (2 chunks)
    ✅ KG Builder: 12 entities, 8 relations
    📊 Graph: 150 nodes, 200 edges
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add path to project for importing modules

from tools.web_scraper import scrape_url
from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from schemas.models import IngestPayload, KGBuilderPayload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def process_url_quick(url: str):
    """
    Quick processing of one URL through TabSage pipeline
    
    Process:
    1. Content download via Web Scraper
    2. Processing via Ingest Agent (normalization, chunking)
    3. Knowledge extraction via KG Builder Agent
    4. Saving to Knowledge Graph
    
    Args:
        url: Article URL to process
    """
    logger.info(f"\n{'='*70}\n📰 Processing URL: {url}\n{'='*70}")
    
    # ============================================================
    # Step 1: Content download
    # ============================================================
    logger.info("📥 Step 1: Downloading content...")
    scraped = scrape_url(url)
    
    if scraped.get("status") != "success":
        logger.error(f"❌ Download error: {scraped.get('error_message')}")
        logger.error("💡 Check:")
        logger.error("   - URL availability")
        logger.error("   - Internet connection")
        logger.error("   - URL correctness")
        return
    
    text = scraped.get("text", "")
    title = scraped.get("title", "N/A")
    logger.info(f"✅ Downloaded: {len(text)} characters")
    logger.info(f"📄 Title: {title}")
    
    # ============================================================
    # Step 2: Ingest Agent - normalization and chunking
    # ============================================================
    logger.info("\n🔄 Step 2: Ingest Agent - normalization and chunking...")
    
    # Create payload for Ingest Agent
    ingest_payload = IngestPayload(
        raw_text=text,
        metadata={"url": url, "source": "habr"},
        session_id="quick_test",
        episode_id="ep_001"
    )
    
    ingest_result = await ingest_run_once(ingest_payload.model_dump())
    
    if "error_message" in ingest_result:
        logger.error(f"❌ Ingest error: {ingest_result['error_message']}")
        return
    
    chunks_count = len(ingest_result.get("chunks", []))
    ingest_title = ingest_result.get("title", "N/A")
    language = ingest_result.get("language", "N/A")
    
    logger.info(f"✅ Ingest completed:")
    logger.info(f"   📝 Title: {ingest_title}")
    logger.info(f"   🌐 Language: {language}")
    logger.info(f"   📦 Chunks: {chunks_count}")
    
    # ============================================================
    # Step 3: KG Builder Agent - knowledge extraction
    # ============================================================
    logger.info("\n🔄 Step 3: KG Builder Agent - entity and relationship extraction...")
    
    # Create payload for KG Builder Agent
    kg_payload = KGBuilderPayload(
        chunks=ingest_result.get("chunks", []),
        title=ingest_result.get("title", ""),
        language=ingest_result.get("language", ""),
        session_id="quick_test",
        episode_id="ep_001"
    )
    
    kg_result = await kg_builder_run_once(kg_payload.model_dump())
    
    if "error_message" in kg_result:
        logger.error(f"❌ KG Builder error: {kg_result['error_message']}")
        return
    
    entities_count = len(kg_result.get("entities", []))
    relations_count = len(kg_result.get("relations", []))
    
    logger.info(f"✅ KG Builder completed:")
    logger.info(f"   🏷️  Entities: {entities_count}")
    logger.info(f"   🔗 Relations: {relations_count}")
    
    # ============================================================
    # Step 4: Graph statistics
    # ============================================================
    logger.info("\n📊 Step 4: Knowledge graph statistics...")
    from tools.kg_client import get_kg_instance
    kg = get_kg_instance()
    stats = kg.get_graph_stats()
    
    logger.info(f"✅ Knowledge graph:")
    logger.info(f"   🔷 Total nodes: {stats.get('nodes_count', 0)}")
    logger.info(f"   🔗 Total edges: {stats.get('edges_count', 0)}")
    logger.info(f"   📄 Articles processed: {stats.get('articles_count', 0)}")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ URL processing completed successfully!")
    logger.info(f"{'='*70}")


async def main():
    # Only 2 URLs for quick demonstration
    urls = [
        "https://habr.com/ru/specials/965986/",
        "https://habr.com/ru/companies/oleg-bunin/articles/537862/"
    ]
    
    print("🚀 Quick URL processing demonstration")
    print(f"Processing {len(urls)} URLs...\n")
    
    for url in urls:
        await process_url_quick(url)
        await asyncio.sleep(1)
    
    print("\n✅ Demonstration completed!")


if __name__ == "__main__":
    asyncio.run(main())

