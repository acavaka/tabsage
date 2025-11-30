#!/usr/bin/env python3
"""
Script to reprocess articles from Firestore

This script allows reprocessing articles that are already in Firestore,
to update their data in Knowledge Graph with correct relationships.

Reprocessing process:
1. Gets articles from Firestore (or specified URLs)
2. Downloads content via Web Scraper
3. Processes via Ingest Agent (normalization, chunking)
4. Extracts knowledge via KG Builder Agent (with correct article_url)
5. Generates summary via Summary Agent
6. Updates article in Firestore with new data

Usage:
    # Reprocess specific URLs
    python scripts/reprocess_articles.py --urls https://habr.com/... https://habr.com/...
    
    # Reprocess all articles from Firestore
    python scripts/reprocess_articles.py --all
    
    # Specify Google Cloud Project ID
    python scripts/reprocess_articles.py --all --project-id your-project-id

Requirements:
    - Google Cloud project configured
    - Firestore configured
    - GEMINI_API_KEY set in config.py
    - All project dependencies installed

Example result:
    ============================================================
    📊 REPROCESSING RESULTS
    ============================================================
    Total: 5
    ✅ Successful: 4
    ❌ Errors: 1
    ============================================================
    
    ✅ Reprocessing completed!
    
    📊 Graph statistics:
      • Articles: 15
      • Entities: 150
      • Relations: 200
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from typing import List, Optional

# Add src to path

from tools.kg_client import get_kg_instance
from tools.web_scraper import scrape_url
from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.summary_agent import run_once as summary_run_once
from schemas.models import IngestPayload, KGBuilderPayload
from observability.logging import get_logger

logger = get_logger(__name__)


async def reprocess_article(url: str, kg) -> dict:
    """
    Reprocesses one article through full pipeline
    
    Process:
    1. Downloads article content via Web Scraper
    2. Processes via Ingest Agent (normalization, chunking)
    3. Extracts knowledge via KG Builder Agent (with correct article_url)
    4. Generates summary via Summary Agent
    5. Updates article in Firestore
    
    Args:
        url: Article URL to reprocess
        kg: Knowledge Graph instance (FirestoreKnowledgeGraph)
        
    Returns:
        Dictionary with processing result:
        {
            "status": "success" | "error",
            "url": str,
            "title": str,
            "entities_count": int,
            "relations_count": int
        }
    """
    try:
        logger.info(f"🔄 Reprocessing article: {url}")
        logger.info("-" * 70)
        
        # ============================================================
        # Step 1: Downloading content
        # ============================================================
        logger.info("  📥 Step 1: Downloading content...")
        scraped = await asyncio.to_thread(scrape_url, url)
        
        if scraped.get("status") != "success":
            error_msg = scraped.get("error_message", "Download error")
            logger.error(f"  ❌ Download error: {error_msg}")
            return {"status": "error", "error": error_msg}
        
        article_text = scraped.get("text", "")
        title = scraped.get("title", "No title")
        
        if not article_text:
            logger.error("  ❌ Empty text after parsing")
            return {"status": "error", "error": "Empty text after parsing"}
        
        logger.info(f"  ✅ Downloaded: {len(article_text)} characters")
        logger.info(f"  📄 Title: {title}")
        
        # ============================================================
        # Step 2: Ingest Agent - normalization and chunking
        # ============================================================
        logger.info(f"  📝 Step 2: Ingest Agent - normalization and chunking...")
        ingest_result = await ingest_run_once(IngestPayload(
            raw_text=article_text,
            metadata={"url": url, "title": title, "source": "reprocess"},
            session_id="reprocess_session",
            episode_id="reprocess_episode"
        ).model_dump())
        
        if "error_message" in ingest_result:
            error_msg = f"Ingest failed: {ingest_result['error_message']}"
            logger.error(f"  ❌ {error_msg}")
            return {"status": "error", "error": error_msg}
        
        chunks_count = len(ingest_result.get('chunks', []))
        logger.info(f"  ✅ Ingest: {chunks_count} chunks created")
        
        # ============================================================
        # Step 3: KG Builder Agent - knowledge extraction
        # ============================================================
        # CRITICAL: pass URL in metadata for correct linking
        # of entities and relationships to article
        logger.info(f"  🔷 Step 3: KG Builder Agent - extracting entities and relationships...")
        kg_payload = KGBuilderPayload(
            chunks=ingest_result.get("chunks", []),
            title=ingest_result.get("title", ""),
            language=ingest_result.get("language", ""),
            session_id="reprocess_session",
            episode_id="reprocess_episode",
            metadata={"url": url}  # CRITICAL: for linking entities/relationships to article
        )
        
        kg_result = await kg_builder_run_once(kg_payload.model_dump())
        
        if "error_message" in kg_result:
            logger.warning(f"  ⚠️ KG Builder failed: {kg_result['error_message']}")
            entities_count = 0
            relations_count = 0
        else:
            entities_count = len(kg_result.get("entities", []))
            relations_count = len(kg_result.get("relations", []))
            logger.info(f"  ✅ KG Builder: {entities_count} entities, {relations_count} relationships")
        
        # ============================================================
        # Step 4: Summary Agent - summary generation
        # ============================================================
        logger.info(f"  📊 Step 4: Summary Agent - generating summary...")
        summary_result = await summary_run_once(
            article_text=article_text,
            title=title,
            url=url
        )
        
        if "error" in summary_result:
            logger.warning(f"  ⚠️ Summary failed: {summary_result.get('error')}")
        else:
            logger.info(f"  ✅ Summary ready")
        
        # ============================================================
        # Step 5: Updating article in Firestore
        # ============================================================
        if hasattr(kg, 'add_article'):
            logger.info(f"  💾 Step 5: Updating article in Firestore...")
            article_data = {
                "url": url,
                "title": title,
                "summary": summary_result.get("summary", ""),
                "key_points": summary_result.get("key_points", []),
                "intents": summary_result.get("intents", []),
                "values": summary_result.get("values", []),
                "trends": summary_result.get("trends", []),
                "unusual_points": summary_result.get("unusual_points", []),
                "ingest_result": ingest_result
            }
            kg.add_article(article_data)
            logger.info(f"  ✅ Article updated in Firestore")
        
        logger.info("-" * 70)
        logger.info(f"✅ Article successfully reprocessed: {title}")
        
        return {
            "status": "success",
            "url": url,
            "title": title,
            "entities_count": entities_count,
            "relations_count": relations_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error reprocessing {url}: {e}", exc_info=True)
        return {"status": "error", "url": url, "error": str(e)}


async def reprocess_all_articles(kg) -> dict:
    """Reprocesses all articles from Firestore.
    
    Args:
        kg: Knowledge Graph instance
        
    Returns:
        Dictionary with results
    """
    try:
        if not hasattr(kg, 'db'):
            logger.error("❌ Firestore not available")
            return {"status": "error", "error": "Firestore not available"}
        
        # Get all articles
        articles_ref = kg.db.collection("articles")
        articles = []
        for article_doc in articles_ref.stream():
            article_data = article_doc.to_dict()
            url = article_data.get("url")
            if url:
                articles.append(url)
        
        logger.info(f"📚 Found {len(articles)} articles for reprocessing")
        
        if not articles:
            return {"status": "error", "error": "No articles found"}
        
        # Reprocess in parallel
        results = await asyncio.gather(
            *[reprocess_article(url, kg) for url in articles],
            return_exceptions=True
        )
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        failed = len(results) - successful
        
        return {
            "status": "success",
            "total": len(articles),
            "successful": successful,
            "failed": failed,
            "results": [r for r in results if isinstance(r, dict)]
        }
        
    except Exception as e:
        logger.error(f"❌ Error reprocessing all articles: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


async def reprocess_urls(urls: List[str], kg) -> dict:
    """Reprocesses specified URLs.
    
    Args:
        urls: List of URLs to reprocess
        kg: Knowledge Graph instance
        
    Returns:
        Dictionary with results
    """
    logger.info(f"📚 Reprocessing {len(urls)} articles")
    
    results = await asyncio.gather(
        *[reprocess_article(url, kg) for url in urls],
        return_exceptions=True
    )
    
    successful = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    failed = len(results) - successful
    
    return {
        "status": "success",
        "total": len(urls),
        "successful": successful,
        "failed": failed,
        "results": [r for r in results if isinstance(r, dict)]
    }


async def main():
    """
    Main script function
    
    Parses command line arguments and starts article reprocessing
    """
    parser = argparse.ArgumentParser(
        description="Reprocessing articles from Firestore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Reprocess specific URLs
  python scripts/reprocess_articles.py --urls https://habr.com/... https://habr.com/...
  
  # Reprocess all articles from Firestore
  python scripts/reprocess_articles.py --all
  
  # Specify Google Cloud Project ID
  python scripts/reprocess_articles.py --all --project-id your-project-id
        """
    )
    parser.add_argument(
        "--urls", 
        nargs="+", 
        help="Article URLs to reprocess (can specify multiple)"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Reprocess all articles from Firestore"
    )
    parser.add_argument(
        "--project-id", 
        help="Google Cloud Project ID (if not specified, uses from environment)"
    )
    
    args = parser.parse_args()
    
    # Initialize environment variables
    os.environ.setdefault("KG_PROVIDER", "firestore")
    if args.project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project_id)
        logger.info(f"📝 Using Google Cloud Project: {args.project_id}")
    
    print("=" * 70)
    print("🔄 REPROCESSING ARTICLES FROM FIRESTORE")
    print("=" * 70)
    print()
    
    # Get Knowledge Graph instance
    kg = get_kg_instance()
    
    # Check that Firestore is used
    if not hasattr(kg, 'db'):
        logger.error("❌ Firestore not available")
        logger.error("💡 Set KG_PROVIDER=firestore and configure Google Cloud project")
        return
    
    logger.info("✅ Firestore connected")
    print()
    
    # Start reprocessing based on arguments
    if args.urls:
        print(f"📋 Reprocessing {len(args.urls)} specified URLs...")
        print()
        result = await reprocess_urls(args.urls, kg)
    elif args.all:
        print("📋 Reprocessing all articles from Firestore...")
        print()
        result = await reprocess_all_articles(kg)
    else:
        logger.error("❌ Specify --urls or --all")
        parser.print_help()
        return
    
    # Output results
    print()
    print("=" * 70)
    print("📊 REPROCESSING RESULTS")
    print("=" * 70)
    print()
    
    total = result.get('total', 0)
    successful = result.get('successful', 0)
    failed = result.get('failed', 0)
    
    print(f"📈 Statistics:")
    print(f"   Total articles: {total}")
    print(f"   ✅ Successfully processed: {successful}")
    print(f"   ❌ Errors: {failed}")
    
    if successful > 0:
        success_rate = (successful / total * 100) if total > 0 else 0
        print(f"   📊 Success rate: {success_rate:.1f}%")
    print()
    
    if result.get("status") == "success":
        print("=" * 70)
        print("✅ Reprocessing completed!")
        print("=" * 70)
        print()
        
        # Show updated graph statistics
        print("📊 Knowledge graph statistics:")
        print("-" * 70)
        stats = kg.get_graph_stats()
        print(f"   📄 Articles: {stats.get('articles_count', 0)}")
        print(f"   🔷 Entities: {stats.get('nodes_count', 0)}")
        print(f"   🔗 Relationships: {stats.get('edges_count', 0)}")
        print()
        
        # Show details by entity types
        entity_types = stats.get('entity_types', {})
        if entity_types:
            print("📋 Entity type distribution:")
            for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {etype}: {count}")
            print()
        
        print("💡 Next steps:")
        print("   - Check updated articles in Firestore")
        print("   - Use examples/view_kg_stats.py to view statistics")
        print("   - Use examples/export_kg.py to export graph")
    else:
        print("=" * 70)
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        print("=" * 70)
        print()
        print("💡 Troubleshooting:")
        print("   - Check Google Cloud project settings")
        print("   - Make sure Firestore is configured correctly")
        print("   - Check GEMINI_API_KEY in config.py")
        print("   - Check article URL availability")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

