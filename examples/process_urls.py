"""Script for processing URL list through TabSage pipeline"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add path to src

from tools.web_scraper import scrape_url
from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.topic_discovery_agent import run_once as topic_discovery_run_once
from schemas.models import IngestPayload, KGBuilderPayload, TopicDiscoveryPayload

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_url(url: str, episode_id: str, session_id: str) -> Dict[str, Any]:
    """Processes one URL through complete pipeline.
    
    Args:
        url: URL to process
        episode_id: Episode ID
        session_id: Session ID
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"=" * 60)
    logger.info(f"Processing URL: {url}")
    logger.info(f"=" * 60)
    
    results = {
        "url": url,
        "episode_id": episode_id,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Step 1: Download content
        logger.info("📥 Downloading content...")
        scraped = scrape_url(url)
        
        if scraped.get("status") != "success":
            results["error"] = scraped.get("error_message", "Download error")
            return results
        
        raw_text = scraped.get("text", "")
        if not raw_text:
            results["error"] = "Empty text after parsing"
            return results
        
        logger.info(f"✅ Downloaded: {len(raw_text)} characters")
        logger.info(f"📄 Title: {scraped.get('title', 'N/A')}")
        
        # Step 2: Ingest
        logger.info("🔄 Ingest Agent: normalization and chunking...")
        ingest_payload = IngestPayload(
            raw_text=raw_text,
            metadata={
                "url": url,
                "title": scraped.get("title", ""),
                "author": scraped.get("author", ""),
                "date": scraped.get("date", ""),
                "source": "habr"
            },
            session_id=session_id,
            episode_id=episode_id
        )
        
        ingest_result = await ingest_run_once(ingest_payload.dict())
        
        if "error_message" in ingest_result:
            results["error"] = f"Ingest failed: {ingest_result['error_message']}"
            return results
        
        results["ingest"] = {
            "title": ingest_result.get("title", ""),
            "language": ingest_result.get("language", ""),
            "chunks_count": len(ingest_result.get("chunks", [])),
            "summary": ingest_result.get("summary", "")[:100] + "..." if len(ingest_result.get("summary", "")) > 100 else ingest_result.get("summary", "")
        }
        
        logger.info(f"✅ Ingest: {results['ingest']['title']}")
        logger.info(f"   Language: {results['ingest']['language']}")
        logger.info(f"   Chunks: {results['ingest']['chunks_count']}")
        
        # Step 3: KG Builder
        logger.info("🔄 KG Builder Agent: extracting entities...")
        kg_payload = KGBuilderPayload(
            chunks=ingest_result.get("chunks", []),
            title=ingest_result.get("title", ""),
            language=ingest_result.get("language", ""),
            session_id=session_id,
            episode_id=episode_id
        )
        
        kg_result = await kg_builder_run_once(kg_payload.dict())
        
        if "error_message" in kg_result:
            results["error"] = f"KG Builder failed: {kg_result['error_message']}"
            return results
        
        entities_count = len(kg_result.get("entities", []))
        relations_count = len(kg_result.get("relations", []))
        
        results["kg_builder"] = {
            "entities_count": entities_count,
            "relations_count": relations_count,
            "graph_updated": kg_result.get("graph_updated", False)
        }
        
        logger.info(f"✅ KG Builder: {entities_count} entities, {relations_count} relations")
        
        # Step 4: Topic Discovery
        logger.info("🔄 Topic Discovery Agent: searching topics...")
        topic_payload = TopicDiscoveryPayload(
            session_id=session_id,
            episode_id=episode_id,
            max_topics=5
        )
        
        topic_result = await topic_discovery_run_once(topic_payload.dict())
        
        if "error_message" in topic_result:
            results["error"] = f"Topic Discovery failed: {topic_result['error_message']}"
            return results
        
        topics = topic_result.get("topics", [])
        results["topic_discovery"] = {
            "topics_count": len(topics),
            "topics": [{"title": t.get("title", ""), "difficulty": t.get("difficulty", "")} for t in topics[:3]]
        }
        
        logger.info(f"✅ Topic Discovery: {len(topics)} topics found")
        for i, topic in enumerate(topics[:3], 1):
            logger.info(f"   {i}. {topic.get('title', 'N/A')} ({topic.get('difficulty', 'N/A')})")
        
        results["status"] = "success"
        logger.info(f"✅ Successfully processed: {url}")
        
    except Exception as e:
        logger.error(f"❌ Error processing {url}: {e}", exc_info=True)
        results["status"] = "error"
        results["error"] = str(e)
    
    return results


async def process_urls(urls: List[str], base_session_id: str = "url_processing") -> List[Dict[str, Any]]:
    """Processes list of URLs.
    
    Args:
        urls: List of URLs to process
        base_session_id: Base session ID
        
    Returns:
        List of processing results
    """
    results = []
    
    for i, url in enumerate(urls, 1):
        episode_id = f"episode_url_{i:03d}"
        session_id = f"{base_session_id}_{i:03d}"
        
        result = await process_url(url, episode_id, session_id)
        results.append(result)
        
        # Small delay between requests
        if i < len(urls):
            await asyncio.sleep(1)
    
    return results


def main():
    """Main function"""
    # List of URLs to process
    urls = [
        "https://habr.com/ru/specials/965986/",
        "https://habr.com/ru/companies/oleg-bunin/articles/537862/",
        "https://habr.com/ru/companies/otus/articles/740578/",
        "https://habr.com/ru/articles/519982/",
        "https://habr.com/ru/articles/658157/",
        "https://habr.com/ru/companies/avito/articles/783534/",
        "https://habr.com/ru/companies/skyeng/articles/714132/",
        "https://habr.com/ru/companies/avito/articles/455068/",
        "https://habr.com/ru/companies/otus/articles/480736/",
        "https://habr.com/ru/companies/raft/articles/931926/"
    ]
    
    print("=" * 60)
    print("TabSage - URL List Processing")
    print("=" * 60)
    print(f"URLs to process: {len(urls)}")
    print()
    
    # Check dependencies
    try:
        import requests
        import bs4
    except ImportError:
        print("❌ Error: Web scraping dependencies not installed")
        print("Install: pip install requests beautifulsoup4")
        return 1
    
    # Run processing
    results = asyncio.run(process_urls(urls))
    
    # Print summary
    print()
    print("=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results if r.get("status") == "success")
    failed = len(results) - successful
    
    print(f"✅ Successfully processed: {successful}/{len(results)}")
    print(f"❌ Errors: {failed}/{len(results)}")
    print()
    
    # Detailed information
    for i, result in enumerate(results, 1):
        url = result.get("url", "N/A")
        status = result.get("status", "unknown")
        
        if status == "success":
            ingest = result.get("ingest", {})
            kg = result.get("kg_builder", {})
            topics = result.get("topic_discovery", {})
            
            print(f"{i}. ✅ {url}")
            print(f"   Title: {ingest.get('title', 'N/A')}")
            print(f"   Entities: {kg.get('entities_count', 0)}, Relations: {kg.get('relations_count', 0)}")
            print(f"   Topics: {topics.get('topics_count', 0)}")
        else:
            error = result.get("error", "Unknown error")
            print(f"{i}. ❌ {url}")
            print(f"   Error: {error}")
        print()
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

